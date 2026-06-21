"""Generate comparison.html from comparison.json."""

from __future__ import annotations

import html
import json
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent / "reports"
COMPARISON_JSON = REPORT_DIR / "comparison.json"
COMPARISON_HTML = REPORT_DIR / "comparison.html"

LABELS = {
    "test": "التجربة",
    "load_balancer": "موزّع الحمل",
    "locking": "نوع القفل",
    "users": "المستخدمون",
    "requests": "الطلبات",
    "failure_pct": "نسبة الفشل %",
    "avg_ms": "متوسط ms",
    "p95_ms": "p95 ms",
    "rps": "RPS",
    "system_up": "النظام شغّال",
    "negative_stock": "مخزون سالب",
    "inventory_ok": "سلامة المخزون",
    "inventory_equation": "معادلة المخزون",
    "deadlocks": "Deadlocks",
    "constraint_violations": "انتهاكات القيد",
    "race_detected": "Race condition",
    "verdict": "النتيجة",
}

TEST_TITLES = {
    "stress_100_users": "اختبار الضغط — 100 مستخدم (الطلب 9)",
    "race_experiment": "تجربة Race — بدون select_for_update (الطلب 7)",
    "lb_lrt": "موزّع LRT — :8080",
    "lb_round_robin": "Round-Robin — :8081",
    "lb_direct": "مباشر web1 — :8001",
}

SECTIONS = [
    ("stress", "اختبار الضغط وسلامة البيانات", ["stress_100_users"]),
    ("race", "مقارنة القفل التشاؤمي", ["race_experiment"]),
    ("lb", "مقارنة موزّعات الحمل (الطلب 5)", ["lb_lrt", "lb_round_robin", "lb_direct"]),
]

GOOD_VERDICTS = {"PASSED", "OK"}
WARN_VERDICTS = {"RACE_DETECTED", "FAILED", "SKIPPED"}


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "نعم ✓" if value else "لا ✗"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return html.escape(str(value))


def _verdict_class(verdict: str | None) -> str:
    if not verdict:
        return "neutral"
    v = verdict.upper()
    if v in GOOD_VERDICTS:
        return "good"
    if v in WARN_VERDICTS:
        return "warn"
    return "neutral"


def _row_by_test(rows: list[dict]) -> dict[str, dict]:
    return {r["test"]: r for r in rows}


def _bar(value: float | None, max_val: float, label: str) -> str:
    if value is None or max_val <= 0:
        return f'<div class="bar-row"><span class="bar-label">{html.escape(label)}</span><span class="bar-empty">—</span></div>'
    pct = min(100, round(value / max_val * 100))
    return (
        f'<div class="bar-row">'
        f'<span class="bar-label">{html.escape(label)}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
        f'<span class="bar-value">{_fmt(value)}</span>'
        f"</div>"
    )


def render_html(data: dict | None = None) -> str:
    if data is None:
        data = json.loads(COMPARISON_JSON.read_text(encoding="utf-8"))
    rows_map = _row_by_test(data.get("rows", []))
    updated = html.escape(data.get("updated_at_utc", "—"))

    parts = [
        """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>تقرير المقارنة — PP E-commerce</title>
  <style>
    :root {
      --bg: #f0f2f5;
      --card: #fff;
      --text: #1a1a2e;
      --muted: #5c6370;
      --border: #e2e6ea;
      --good: #0d7a3e;
      --good-bg: #d4edda;
      --warn: #b45309;
      --warn-bg: #fef3c7;
      --accent: #1e40af;
      --accent-light: #dbeafe;
    }
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1.5rem;
      line-height: 1.5;
    }
    .wrap { max-width: 1100px; margin: 0 auto; }
    header {
      background: linear-gradient(135deg, #1e3a8a, #2563eb);
      color: #fff;
      border-radius: 12px;
      padding: 1.5rem 2rem;
      margin-bottom: 1.5rem;
    }
    header h1 { margin: 0 0 .4rem; font-size: 1.5rem; }
    header p { margin: 0; opacity: .9; font-size: .95rem; }
    .card {
      background: var(--card);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.25rem;
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    .card h2 {
      margin: 0 0 1rem;
      font-size: 1.1rem;
      color: var(--accent);
      border-bottom: 2px solid var(--accent-light);
      padding-bottom: .5rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: .92rem;
    }
    th, td {
      border: 1px solid var(--border);
      padding: .55rem .75rem;
      text-align: center;
    }
    th { background: #eef2f7; font-weight: 600; }
    tr:nth-child(even) td { background: #fafbfc; }
    .badge {
      display: inline-block;
      padding: .25rem .75rem;
      border-radius: 999px;
      font-weight: 700;
      font-size: .85rem;
    }
    .badge.good { background: var(--good-bg); color: var(--good); }
    .badge.warn { background: var(--warn-bg); color: var(--warn); }
    .badge.neutral { background: #e5e7eb; color: #374151; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: .75rem;
      margin-top: .5rem;
    }
    .metric {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: .75rem;
      text-align: center;
    }
    .metric strong {
      display: block;
      font-size: 1.35rem;
      color: var(--accent);
    }
    .metric span { font-size: .8rem; color: var(--muted); }
    .equation {
      font-family: Consolas, monospace;
      background: var(--accent-light);
      padding: .75rem 1rem;
      border-radius: 8px;
      text-align: center;
      font-size: 1.05rem;
      margin: .75rem 0;
    }
    .lb-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    .lb-card {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
      background: #fafbfc;
    }
    .lb-card h3 { margin: 0 0 .75rem; font-size: 1rem; }
    .bar-row {
      display: grid;
      grid-template-columns: 70px 1fr 60px;
      align-items: center;
      gap: .5rem;
      margin-bottom: .45rem;
      font-size: .82rem;
    }
    .bar-label { color: var(--muted); text-align: right; }
    .bar-track {
      height: 10px;
      background: #e5e7eb;
      border-radius: 5px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #1d4ed8);
      border-radius: 5px;
    }
    .bar-value { font-weight: 600; text-align: left; }
    .bar-empty { color: var(--muted); grid-column: 2; }
    .compare-table th:first-child,
    .compare-table td:first-child { text-align: right; font-weight: 500; }
    footer {
      text-align: center;
      color: var(--muted);
      font-size: .82rem;
      margin-top: 1.5rem;
    }
    @media print {
      body { background: #fff; padding: 0; }
      .card { box-shadow: none; break-inside: avoid; }
    }
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>تقرير مقارنة اختبارات الأداء والتزامن</h1>
    <p>PP E-commerce Project — Non-Functional Requirements (5–10)</p>
    <p>آخر تحديث: """,
        updated,
        """</p>
  </header>
""",
    ]

    # ── Summary table (all rows) ──
    parts.append('<section class="card"><h2>جدول المقارنة الشامل</h2><div style="overflow-x:auto"><table class="compare-table"><thead><tr>')
    display_cols = [
        "test", "load_balancer", "locking", "users", "requests",
        "failure_pct", "avg_ms", "p95_ms", "rps", "verdict",
    ]
    for col in display_cols:
        parts.append(f"<th>{html.escape(LABELS[col])}</th>")
    parts.append("</tr></thead><tbody>")

    for row in data.get("rows", []):
        parts.append("<tr>")
        for col in display_cols:
            val = row.get(col)
            if col == "verdict":
                cls = _verdict_class(val)
                parts.append(f'<td><span class="badge {cls}">{_fmt(val)}</span></td>')
            elif col == "test":
                title = TEST_TITLES.get(val, val)
                parts.append(f"<td>{html.escape(title)}</td>")
            else:
                parts.append(f"<td>{_fmt(val)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div></section>")

    # ── Section: Stress test ──
    stress = rows_map.get("stress_100_users")
    if stress:
        parts.append('<section class="card"><h2>الطلب 9 — اختبار الاستقرار تحت الضغط</h2>')
        parts.append('<div class="metric-grid">')
        for key, label in [
            ("users", "مستخدم متزامن"),
            ("requests", "إجمالي الطلبات"),
            ("failure_pct", "نسبة الفشل %"),
            ("rps", "Throughput RPS"),
            ("p95_ms", "p95 (ms)"),
        ]:
            parts.append(
                f'<div class="metric"><strong>{_fmt(stress.get(key))}</strong>'
                f"<span>{html.escape(label)}</span></div>"
            )
        parts.append("</div>")
        if stress.get("inventory_equation"):
            parts.append(f'<div class="equation">{_fmt(stress["inventory_equation"])}</div>')
            parts.append("<p style=\"text-align:center;color:var(--muted);margin:0\">"
                         "المخزون الابتدائي = النهائي + المباع أثناء الاختبار</p>")
        parts.append('<div class="metric-grid" style="margin-top:1rem">')
        for key, label in [
            ("system_up", "النظام بقي شغّالاً"),
            ("negative_stock", "منتجات بمخزون سالب"),
            ("inventory_ok", "سلامة المخزون"),
            ("deadlocks", "Deadlocks"),
        ]:
            parts.append(
                f'<div class="metric"><strong>{_fmt(stress.get(key))}</strong>'
                f"<span>{html.escape(label)}</span></div>"
            )
        cls = _verdict_class(stress.get("verdict"))
        parts.append(
            f'</div><p style="margin-top:1rem;text-align:center">'
            f'النتيجة: <span class="badge {cls}">{_fmt(stress.get("verdict"))}</span></p></section>'
        )

    # ── Section: Race experiment ──
    race = rows_map.get("race_experiment")
    lock_stress = rows_map.get("stress_100_users")
    if race:
        parts.append('<section class="card"><h2>الطلب 7 — مع القفل vs بدون القفل</h2>')
        parts.append('<table><thead><tr><th></th><th>مع select_for_update</th><th>بدون select_for_update</th></tr></thead><tbody>')
        compare_rows = [
            ("Deadlocks", lock_stress.get("deadlocks") if lock_stress else 0, race.get("deadlocks")),
            ("انتهاكات القيد", lock_stress.get("constraint_violations") if lock_stress else 0, race.get("constraint_violations")),
            ("Race detected", lock_stress.get("race_detected") if lock_stress else False, race.get("race_detected")),
            ("مخزون سالب", lock_stress.get("negative_stock") if lock_stress else 0, race.get("negative_stock")),
            ("النتيجة", lock_stress.get("verdict") if lock_stress else "—", race.get("verdict")),
        ]
        for label, with_lock, without in compare_rows:
            if label == "النتيجة":
                parts.append(
                    f"<tr><td>{label}</td>"
                    f'<td><span class="badge {_verdict_class(with_lock)}">{_fmt(with_lock)}</span></td>'
                    f'<td><span class="badge {_verdict_class(without)}">{_fmt(without)}</span></td></tr>'
                )
            else:
                parts.append(f"<tr><td>{label}</td><td>{_fmt(with_lock)}</td><td>{_fmt(without)}</td></tr>")
        parts.append("</tbody></table></section>")

    # ── Section: Load balancer ──
    lb_rows = [rows_map[k] for k in ("lb_lrt", "lb_round_robin", "lb_direct") if k in rows_map]
    if lb_rows:
        max_rps = max((r.get("rps") or 0) for r in lb_rows)
        max_p95 = max((r.get("p95_ms") or 0) for r in lb_rows)
        max_req = max((r.get("requests") or 0) for r in lb_rows)

        parts.append('<section class="card"><h2>الطلب 5 — مقارنة موزّعات الحمل</h2>')
        parts.append('<div class="lb-grid">')
        for row in lb_rows:
            title = TEST_TITLES.get(row["test"], row["test"])
            cls = _verdict_class(row.get("verdict"))
            parts.append(f'<div class="lb-card"><h3>{html.escape(title)} '
                         f'<span class="badge {cls}">{_fmt(row.get("verdict"))}</span></h3>')
            parts.append(_bar(row.get("rps"), max_rps, "RPS"))
            parts.append(_bar(row.get("p95_ms"), max_p95, "p95"))
            parts.append(_bar(row.get("requests"), max_req, "طلبات"))
            parts.append(
                f'<p style="margin:.75rem 0 0;font-size:.85rem;color:var(--muted)">'
                f'avg: {_fmt(row.get("avg_ms"))} ms · فشل: {_fmt(row.get("failure_pct"))}%</p>'
            )
            parts.append("</div>")
        parts.append("</div></section>")

    parts.append(
        '<footer>Generated from stress_test/reports/comparison.json · '
        'python stress_test/render_html.py</footer>'
        "</div></body></html>"
    )
    return "".join(parts)


def write_html(path: Path | None = None) -> Path:
    path = path or COMPARISON_HTML
    if not COMPARISON_JSON.exists():
        raise FileNotFoundError(f"Missing {COMPARISON_JSON}")
    content = render_html()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


if __name__ == "__main__":
    out = write_html()
    print(f"Written: {out}")
