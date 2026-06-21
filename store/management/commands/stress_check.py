import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Sum

from store.models import Order, Product, ProductOrder


class Command(BaseCommand):
    help = "Stress test DB check: --snapshot before test, --verify after."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--snapshot", action="store_true")
        group.add_argument("--verify", action="store_true")
        parser.add_argument(
            "--baseline",
            default="stress_test/snapshots/baseline.json",
        )
        parser.add_argument(
            "--output",
            default="stress_test/reports/integrity.json",
        )

    def handle(self, *args, **options):
        if options["snapshot"]:
            self._snapshot(options["baseline"])
        else:
            self._verify(options["baseline"], options["output"])

    def _snapshot(self, path: str) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        sold = ProductOrder.objects.aggregate(t=Sum("quantity"))["t"] or 0
        data = {
            "orders_count": Order.objects.count(),
            "inventory_units": Product.objects.aggregate(t=Sum("quantity"))["t"] or 0,
            "sold_units": int(sold),
        }
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Snapshot → {path}"))

    def _verify(self, baseline_path: str, output_path: str) -> None:
        base_file = Path(baseline_path)
        if not base_file.exists():
            self.stderr.write(self.style.ERROR(f"Missing {baseline_path}"))
            return

        baseline = json.loads(base_file.read_text(encoding="utf-8"))
        negative = Product.objects.filter(quantity__lt=0).count()
        current_inv = Product.objects.aggregate(t=Sum("quantity"))["t"] or 0
        current_sold = ProductOrder.objects.aggregate(t=Sum("quantity"))["t"] or 0

        start_inv = int(baseline["inventory_units"])
        new_sold = int(current_sold) - int(baseline["sold_units"])
        inventory_ok = int(current_inv) == start_inv - new_sold
        passed = negative == 0 and inventory_ok

        result = {
            "passed": passed,
            "negative_stock": negative,
            "inventory_ok": inventory_ok,
            "inventory_equation": f"{start_inv} = {current_inv} + {new_sold}",
            "new_orders": Order.objects.count() - int(baseline["orders_count"]),
            "new_sold": new_sold,
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

        if passed:
            self.stdout.write(self.style.SUCCESS("Integrity PASSED"))
        else:
            self.stdout.write(self.style.ERROR("Integrity FAILED"))
        self.stdout.write(str(result))
