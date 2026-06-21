"""
Stress test runner ,  all experiments update reports/comparison.json

Usage:
  python stress_test/run.py stress          # 100 users + pessimistic lock
  python stress_test/run.py race             # race condition without lock
  python stress_test/run.py lb              # LRT vs Round-Robin vs direct
  python stress_test/run.py all             # run everything

Output: stress_test/reports/comparison.json + comparison.html
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DIR = Path(__file__).resolve().parent
REPORTS = DIR / "reports"
SNAPSHOT = DIR / "snapshots" / "baseline.json"
INTEGRITY = REPORTS / "integrity.json"

sys.path.insert(0, str(ROOT))
from stress_test.comparison import row_lb, row_with_lock, row_without_lock, upsert_row  # noqa: E402


# helpers

def db_env() -> dict:
    env = os.environ.copy()
    env.setdefault("DB_HOST", "127.0.0.1")
    env.setdefault("DB_PORT", "3307")
    env.setdefault("DB_USER", "root")
    env.setdefault("DB_PASSWORD", "rootpass")
    env.setdefault("DB_NAME", "store")
    env.setdefault("DJANGO_SECRET_KEY", "docker-dev-secret-key")
    return env


def run(cmd: list[str], env: dict | None = None) -> None:
    print(">>", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, env=env or db_env(), check=False)


def health(host: str, *, timeout=15, retries=1) -> bool:
    url = f"{host.rstrip('/')}/api/product/all"
    for i in range(retries):
        try:
            with urlopen(url, timeout=timeout) as r:
                return r.status == 200
        except Exception:
            if i + 1 < retries:
                time.sleep(3)
    return False


def django_cmd(args: list[str], docker: bool, env: dict) -> None:
    if docker:
        run(["docker", "compose", "exec", "-T", "web1", "python", "manage.py", *args], env)
    else:
        run([sys.executable, "manage.py", *args], env)


def docker_copy(src: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(["docker", "cp", f"pp-ecommerce-project-web1-1:{src}", str(dst)], os.environ.copy())


def locust_stats(csv_prefix: Path) -> dict:
    f = Path(f"{csv_prefix}_stats.csv")
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as h:
        for row in csv.DictReader(h):
            if row.get("Name") != "Aggregated":
                continue
            total = int(float(row["Request Count"]))
            fail = int(float(row["Failure Count"]))
            return {
                "requests": total,
                "failure_pct": round(fail / total * 100, 2) if total else 0.0,
                "avg_ms": round(float(row["Average Response Time"]), 2),
                "p95_ms": round(float(row["95%"]), 2),
                "rps": round(float(row["Requests/s"]), 2),
            }
    return {}


def run_locust(host: str, users: int, spawn: int, duration: str, csv_prefix: Path, locustfile: str) -> None:
    run([
        "locust", "-f", locustfile,
        f"--host={host}", f"--users={users}", f"--spawn-rate={spawn}",
        f"--run-time={duration}", "--headless", f"--csv={csv_prefix}",
    ])


# experiments
def cmd_stress(args: argparse.Namespace) -> int:
    host = args.host
    docker = (not args.local_django) and ":8080" in host
    env = db_env()

    if not health(host, retries=3):
        print(f"ERROR: {host} not reachable — run: docker compose up -d")
        return 1

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    django_cmd(["stress_check", "--snapshot"], docker, env)
    if docker:
        docker_copy("/app/stress_test/snapshots/baseline.json", SNAPSHOT)

    csv = REPORTS / "locust"
    if not args.skip_locust:
        run_locust(host, args.users, args.spawn_rate, args.run_time, csv, "locustfile.py")

    time.sleep(5)
    up = health(host, timeout=30, retries=5)
    django_cmd(["stress_check", "--verify"], docker, env)
    if docker:
        docker_copy("/app/stress_test/reports/integrity.json", INTEGRITY)

    integrity = json.loads(INTEGRITY.read_text(encoding="utf-8"))
    stats = locust_stats(csv)

    upsert_row(row_with_lock(
        users=args.users,
        requests=stats.get("requests", 0),
        failure_pct=stats.get("failure_pct", 0.0),
        avg_ms=stats.get("avg_ms"),
        p95_ms=stats.get("p95_ms"),
        rps=stats.get("rps"),
        system_up=up,
        negative_stock=integrity["negative_stock"],
        inventory_ok=integrity["inventory_ok"],
        inventory_equation=integrity["inventory_equation"],
        verdict="PASSED" if integrity["passed"] else "FAILED",
    ))
    return 0 if integrity["passed"] else 2


def cmd_race(_args: argparse.Namespace) -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    for k, v in db_env().items():
        os.environ.setdefault(k, v)

    import django
    django.setup()

    from django.contrib.auth.models import User
    from store.models import Bank, Cart, CartProduct, Order, Product, ProductOrder
    from stress_test.race_checkout import checkout_without_lock

    trials, buyers = 10, 5

    def classify(msg: str) -> str:
        u = msg.upper()
        if "PRODUCT_QUANTITY_NON_NEGATIVE" in u or "4025" in u:
            return "constraint"
        if "DEADLOCK" in u or "1213" in u:
            return "deadlock"
        return "other"

    def cleanup():
        ProductOrder.objects.filter(order__user__username__startswith="nolock_").delete()
        Order.objects.filter(user__username__startswith="nolock_").delete()
        CartProduct.objects.filter(cart__user__username__startswith="nolock_").delete()
        Cart.objects.filter(user__username__startswith="nolock_").delete()
        Bank.objects.filter(user__username__startswith="nolock_").delete()
        User.objects.filter(username__startswith="nolock_").delete()
        Product.objects.filter(name="NoLock Race Product").delete()

    totals = {"deadlocks": 0, "constraints": 0, "race_trials": 0}

    for n in range(1, trials + 1):
        cleanup()
        product = Product.objects.create(name="NoLock Race Product", price=Decimal("50"), quantity=1)
        users = []
        for i in range(buyers):
            u = User.objects.create_user(username=f"nolock_{n}_{i}", password="p", email=f"{n}_{i}@t.l")
            Bank.objects.create(user=u, balance=Decimal("1000"))
            cart = Cart.objects.create(user=u)
            CartProduct.objects.create(cart=cart, product=product, quantity=1)
            users.append(u)

        stats = {"deadlocks": 0, "constraints": 0}
        lock = threading.Lock()
        barrier = threading.Barrier(buyers)

        def attempt(user):
            try:
                barrier.wait()
                order, error, _ = checkout_without_lock(user, force_payment_success=True)
                if not order and error:
                    kind = classify(error)
                    with lock:
                        if kind == "deadlock":
                            stats["deadlocks"] += 1
                        elif kind == "constraint":
                            stats["constraints"] += 1
            except Exception as exc:
                kind = classify(str(exc))
                with lock:
                    if kind == "deadlock":
                        stats["deadlocks"] += 1
                    elif kind == "constraint":
                        stats["constraints"] += 1

        threads = [threading.Thread(target=attempt, args=(u,)) for u in users]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        race = stats["deadlocks"] > 0 or stats["constraints"] > 0
        totals["deadlocks"] += stats["deadlocks"]
        totals["constraints"] += stats["constraints"]
        totals["race_trials"] += int(race)
        cleanup()
        print(f"  trial {n}: deadlock={stats['deadlocks']} constraint={stats['constraints']}")

    race_detected = totals["race_trials"] > 0
    upsert_row(row_without_lock(
        users=buyers,
        requests=trials * buyers,
        negative_stock=0,
        deadlocks=totals["deadlocks"],
        constraint_violations=totals["constraints"],
        race_detected=race_detected,
        verdict="RACE_DETECTED" if race_detected else "OK",
    ))
    return 0


def cmd_lb(_args: argparse.Namespace) -> int:
    modes = [
        ("lb_lrt", "lrt", "http://localhost:8080"),
        ("lb_round_robin", "round_robin", "http://localhost:8081"),
        ("lb_direct", "none", "http://localhost:8001"),
    ]
    csv = REPORTS / "locust_lb"
    users, spawn, duration = 50, 10, "1m"

    for test, lb, host in modes:
        print(f"\n--- {test} ({host}) ---")
        if not health(host):
            upsert_row(row_lb(test=test, load_balancer=lb, users=users, requests=0,
                               failure_pct=0, avg_ms=0, p95_ms=0, rps=0,
                               system_up=False, verdict="SKIPPED"))
            continue

        run_locust(host, users, spawn, duration, csv, "stress_test/locust_read.py")
        time.sleep(2)
        stats = locust_stats(csv)
        up = health(host)
        upsert_row(row_lb(
            test=test, load_balancer=lb, users=users,
            requests=stats.get("requests", 0),
            failure_pct=stats.get("failure_pct", 0.0),
            avg_ms=stats.get("avg_ms", 0.0),
            p95_ms=stats.get("p95_ms", 0.0),
            rps=stats.get("rps", 0.0),
            system_up=up,
            verdict="OK" if up and stats.get("requests", 0) else "FAILED",
        ))
        print(f"  p95={stats.get('p95_ms')}ms  rps={stats.get('rps')}")

    return 0


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Stress test experiments")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stress = sub.add_parser("stress", help="100 users with pessimistic lock")
    p_stress.add_argument("--host", default="http://localhost:8080")
    p_stress.add_argument("--users", type=int, default=100)
    p_stress.add_argument("--spawn-rate", type=int, default=10)
    p_stress.add_argument("--run-time", default="3m")
    p_stress.add_argument("--local-django", action="store_true")
    p_stress.add_argument("--skip-locust", action="store_true")

    sub.add_parser("race", help="race condition without select_for_update")
    sub.add_parser("lb", help="LRT vs Round-Robin vs direct")
    sub.add_parser("all", help="run stress + race + lb")

    args = parser.parse_args()

    if args.cmd == "all":
        stress_args = argparse.Namespace(
            host="http://localhost:8080",
            users=100,
            spawn_rate=10,
            run_time="3m",
            local_django=False,
            skip_locust=False,
        )
        code = cmd_stress(stress_args)
        code = cmd_race(args) or code
        code = cmd_lb(args) or code
    elif args.cmd == "stress":
        code = cmd_stress(args)
    elif args.cmd == "race":
        code = cmd_race(args)
    else:
        code = cmd_lb(args)

    print(f"\nResults → stress_test/reports/comparison.json")
    try:
        from stress_test.render_html import write_html
        html_path = write_html()
        print(f"HTML report → {html_path}")
    except Exception as exc:
        print(f"HTML report skipped: {exc}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
