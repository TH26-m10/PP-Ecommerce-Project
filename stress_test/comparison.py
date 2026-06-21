"""Read/write stress_test/reports/comparison.json"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent / "reports"
COMPARISON_FILE = REPORT_DIR / "comparison.json"

COLUMNS = [
    "test",
    "load_balancer",
    "locking",
    "users",
    "requests",
    "failure_pct",
    "avg_ms",
    "p95_ms",
    "rps",
    "system_up",
    "negative_stock",
    "inventory_ok",
    "inventory_equation",
    "deadlocks",
    "constraint_violations",
    "race_detected",
    "verdict",
]


def empty_comparison() -> dict:
    return {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "columns": COLUMNS,
        "rows": [],
    }


def load_comparison() -> dict:
    if not COMPARISON_FILE.exists():
        return empty_comparison()
    data = json.loads(COMPARISON_FILE.read_text(encoding="utf-8"))
    data["columns"] = COLUMNS
    data.setdefault("rows", [])
    return data


def upsert_row(row: dict) -> dict:
    data = load_comparison()
    data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    data["columns"] = COLUMNS
    rows = [r for r in data["rows"] if r.get("test") != row.get("test")]
    rows.append({col: row.get(col) for col in COLUMNS})
    data["rows"] = rows
    COMPARISON_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        from stress_test.render_html import write_html
        write_html()
    except Exception:
        pass
    return data


def row_with_lock(
    *,
    users: int,
    requests: int,
    failure_pct: float,
    avg_ms: float | None,
    p95_ms: float | None,
    rps: float | None,
    system_up: bool,
    negative_stock: int,
    inventory_ok: bool,
    inventory_equation: str,
    verdict: str,
) -> dict:
    return {
        "test": "stress_100_users",
        "load_balancer": "lrt",
        "locking": "select_for_update",
        "users": users,
        "requests": requests,
        "failure_pct": failure_pct,
        "avg_ms": avg_ms,
        "p95_ms": p95_ms,
        "rps": rps,
        "system_up": system_up,
        "negative_stock": negative_stock,
        "inventory_ok": inventory_ok,
        "inventory_equation": inventory_equation,
        "deadlocks": 0,
        "constraint_violations": 0,
        "race_detected": False,
        "verdict": verdict,
    }


def row_without_lock(
    *,
    users: int,
    requests: int,
    negative_stock: int,
    deadlocks: int,
    constraint_violations: int,
    race_detected: bool,
    verdict: str,
) -> dict:
    return {
        "test": "race_experiment",
        "load_balancer": None,
        "locking": "none",
        "users": users,
        "requests": requests,
        "failure_pct": None,
        "avg_ms": None,
        "p95_ms": None,
        "rps": None,
        "system_up": True,
        "negative_stock": negative_stock,
        "inventory_ok": not race_detected,
        "inventory_equation": None,
        "deadlocks": deadlocks,
        "constraint_violations": constraint_violations,
        "race_detected": race_detected,
        "verdict": verdict,
    }


def row_lb(
    *,
    test: str,
    load_balancer: str,
    users: int,
    requests: int,
    failure_pct: float,
    avg_ms: float,
    p95_ms: float,
    rps: float,
    system_up: bool,
    verdict: str,
) -> dict:
    return {
        "test": test,
        "load_balancer": load_balancer,
        "locking": None,
        "users": users,
        "requests": requests,
        "failure_pct": failure_pct,
        "avg_ms": avg_ms,
        "p95_ms": p95_ms,
        "rps": rps,
        "system_up": system_up,
        "negative_stock": None,
        "inventory_ok": None,
        "inventory_equation": None,
        "deadlocks": None,
        "constraint_violations": None,
        "race_detected": None,
        "verdict": verdict,
    }
