"""Command-line interface.

    python -m auditor bill.csv                     # print the audit
    python -m auditor bill.csv --pdf report.pdf --xlsx report.xlsx --lang ar
    python -m auditor bill.csv --fail-over 500     # exit 1 if savings > $500 (CI gate)
    python -m auditor --sample aws --out sample.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analytics, parsing, report, rules, samples
from .i18n import AR, EN


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m auditor", description="Audit a cloud bill for waste.")
    ap.add_argument("bill", nargs="?", help="Billing export (csv, csv.gz, zip, xlsx, json, parquet)")
    ap.add_argument("--lang", choices=["en", "ar"], default="en")
    ap.add_argument("--pdf"), ap.add_argument("--xlsx"), ap.add_argument("--md")
    ap.add_argument("--fail-over", type=float, help="Exit with code 1 if potential savings exceed this amount")
    ap.add_argument("--sample", choices=["aws", "gcp", "azure"], help="Generate a sample bill instead")
    ap.add_argument("--out", help="Where to write the sample bill (with --sample)")
    args = ap.parse_args(argv)

    if args.sample:
        df = samples.generate({"aws": "AWS", "gcp": "GCP", "azure": "Azure"}[args.sample])
        out = args.out or f"sample_{args.sample}_bill.csv"
        df.to_csv(out, index=False)
        print(f"Sample bill written to {out} ({len(df)} line items)")
        return 0
    if not args.bill:
        ap.error("a bill file is required (or use --sample)")

    lang = AR if args.lang == "ar" else EN
    path = Path(args.bill)
    bill = parsing.load_bill(path.read_bytes(), path.name)
    s = analytics.summarize(bill)
    a = rules.run_rules(bill, s, lang)

    print(report.to_markdown(bill, s, a, lang))
    for flag, fn, mode in ((args.pdf, report.to_pdf, "wb"), (args.xlsx, report.to_excel, "wb")):
        if flag:
            Path(flag).write_bytes(fn(bill, s, a, lang))
            print(f"→ {flag}", file=sys.stderr)
    if args.md:
        Path(args.md).write_text(report.to_markdown(bill, s, a, lang), encoding="utf-8")
        print(f"→ {args.md}", file=sys.stderr)

    if args.fail_over is not None and a.total_savings > args.fail_over:
        print(f"Potential savings ${a.total_savings:,.2f} exceed threshold ${args.fail_over:,.2f}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
