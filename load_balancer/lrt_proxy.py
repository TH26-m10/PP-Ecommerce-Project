"""
Least Response Time reverse proxy for multiple Django backends.

Routes each request to the backend with the lowest rolling average response time.
Exposes GET /lb/status for monitoring without touching Django application code.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI, Request, Response

WINDOW = int(os.environ.get("LRT_WINDOW", "20"))
HEALTH_PATH = os.environ.get("LRT_HEALTH_PATH", "/api/product/all")
HEALTH_INTERVAL = int(os.environ.get("LRT_HEALTH_INTERVAL", "15"))


def _parse_backends(raw: str) -> list[str]:
    return [url.strip().rstrip("/") for url in raw.split(",") if url.strip()]


@dataclass
class Backend:
    url: str
    name: str
    times: deque[float] = field(default_factory=lambda: deque(maxlen=WINDOW))
    healthy: bool = True
    last_error: str | None = None

    def avg_ms(self) -> float | None:
        if not self.times:
            return None
        return sum(self.times) / len(self.times)

    def score(self) -> float:
        """Lower is better. Unknown backends start at 0 to receive initial traffic."""
        avg = self.avg_ms()
        return avg if avg is not None else 0.0


def _backend_name(url: str) -> str:
    # http://web1:8000 -> web1
    host = url.split("//", 1)[-1]
    return host.split(":")[0]


BACKEND_URLS = _parse_backends(
    os.environ.get(
        "BACKENDS",
        "http://web1:8000,http://web2:8000,http://web3:8000",
    )
)
backends: list[Backend] = [
    Backend(url=url, name=_backend_name(url)) for url in BACKEND_URLS
]

app = FastAPI(title="LRT Load Balancer", docs_url=None, redoc_url=None)
_client: httpx.AsyncClient | None = None


def pick_backend() -> Backend:
    pool = [b for b in backends if b.healthy] or backends
    return min(pool, key=lambda b: b.score())


@app.on_event("startup")
async def startup() -> None:
    global _client
    _client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    asyncio.create_task(_health_loop())


@app.on_event("shutdown")
async def shutdown() -> None:
    if _client:
        await _client.aclose()


async def _health_loop() -> None:
    while True:
        await asyncio.sleep(HEALTH_INTERVAL)
        if not _client:
            continue
        for backend in backends:
            try:
                resp = await _client.get(f"{backend.url}{HEALTH_PATH}")
                backend.healthy = resp.status_code < 500
                backend.last_error = None if backend.healthy else f"HTTP {resp.status_code}"
            except Exception as exc:
                backend.healthy = False
                backend.last_error = str(exc)


@app.get("/lb/status")
async def lb_status() -> dict:
    return {
        "strategy": "least_response_time",
        "window": WINDOW,
        "backends": [
            {
                "name": b.name,
                "url": b.url,
                "healthy": b.healthy,
                "avg_response_ms": round(b.avg_ms(), 2) if b.avg_ms() is not None else None,
                "samples": len(b.times),
                "last_error": b.last_error,
            }
            for b in backends
        ],
    }


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request) -> Response:
    if not _client:
        return Response("Load balancer not ready", status_code=503)

    backend = pick_backend()
    target = f"{backend.url}/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length"}
    }
    body = await request.body()

    start = time.perf_counter()
    try:
        upstream = await _client.request(
            request.method,
            target,
            content=body,
            headers=headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        backend.times.append(elapsed_ms)
        backend.healthy = True
        backend.last_error = None

        response_headers = dict(upstream.headers)
        response_headers["X-LB-Strategy"] = "least_response_time"
        response_headers["X-LB-Backend"] = backend.name
        response_headers["X-LB-Response-Ms"] = f"{elapsed_ms:.2f}"

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )
    except Exception as exc:
        backend.healthy = False
        backend.last_error = str(exc)
        return Response(
            content=f"Backend unavailable: {backend.name}",
            status_code=502,
            media_type="text/plain",
        )
