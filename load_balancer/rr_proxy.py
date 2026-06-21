"""Simple round-robin reverse proxy (no Least Response Time)."""

from __future__ import annotations

import asyncio
import itertools
import os
import time

import httpx
from fastapi import FastAPI, Request, Response

HEALTH_PATH = os.environ.get("LRT_HEALTH_PATH", "/api/product/all")
HEALTH_INTERVAL = int(os.environ.get("LRT_HEALTH_INTERVAL", "15"))


def _parse_backends(raw: str) -> list[str]:
    return [url.strip().rstrip("/") for url in raw.split(",") if url.strip()]


def _backend_name(url: str) -> str:
    return url.split("//", 1)[-1].split(":")[0]


BACKEND_URLS = _parse_backends(
    os.environ.get(
        "BACKENDS",
        "http://web1:8000,http://web2:8000,http://web3:8000",
    )
)
BACKEND_NAMES = [_backend_name(url) for url in BACKEND_URLS]
healthy: dict[str, bool] = {url: True for url in BACKEND_URLS}
last_errors: dict[str, str | None] = {url: None for url in BACKEND_URLS}
_cycle = itertools.cycle(range(len(BACKEND_URLS)))

app = FastAPI(title="Round-Robin Load Balancer", docs_url=None, redoc_url=None)
_client: httpx.AsyncClient | None = None


def pick_backend() -> tuple[str, str]:
    n = len(BACKEND_URLS)
    for _ in range(n):
        idx = next(_cycle)
        url = BACKEND_URLS[idx]
        if healthy.get(url, True):
            return url, BACKEND_NAMES[idx]
    url = BACKEND_URLS[0]
    return url, BACKEND_NAMES[0]


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
        for url in BACKEND_URLS:
            try:
                resp = await _client.get(f"{url}{HEALTH_PATH}")
                healthy[url] = resp.status_code < 500
                last_errors[url] = None if healthy[url] else f"HTTP {resp.status_code}"
            except Exception as exc:
                healthy[url] = False
                last_errors[url] = str(exc)


@app.get("/lb/status")
async def lb_status() -> dict:
    return {
        "strategy": "round_robin",
        "backends": [
            {
                "name": BACKEND_NAMES[i],
                "url": BACKEND_URLS[i],
                "healthy": healthy.get(BACKEND_URLS[i], True),
                "last_error": last_errors.get(BACKEND_URLS[i]),
            }
            for i in range(len(BACKEND_URLS))
        ],
    }


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request) -> Response:
    if not _client:
        return Response("Load balancer not ready", status_code=503)

    backend_url, backend_name = pick_backend()
    target = f"{backend_url}/{path}"
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
            request.method, target, content=body, headers=headers
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        response_headers = dict(upstream.headers)
        response_headers["X-LB-Strategy"] = "round_robin"
        response_headers["X-LB-Backend"] = backend_name
        response_headers["X-LB-Response-Ms"] = f"{elapsed_ms:.2f}"
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )
    except Exception as exc:
        last_errors[backend_url] = str(exc)
        healthy[backend_url] = False
        return Response(
            content=f"Backend unavailable: {backend_name}",
            status_code=502,
            media_type="text/plain",
        )
