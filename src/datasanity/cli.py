from __future__ import annotations

import argparse
from pathlib import Path
from .core import DataSanityConfig, audit_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="datasanity", description="Audit CSV/Excel tables for common data-quality problems.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Run data sanity checks")
    check.add_argument("path")
    check.add_argument("--missingness-threshold", type=float, default=0.30)
    check.add_argument("--id-column", action="append", default=[])
    check.add_argument("--format", choices=["text", "json", "html"], default="text")
    check.add_argument("--output", "-o")
    args = parser.parse_args(argv)

    config = DataSanityConfig(missingness_threshold=args.missingness_threshold, id_columns=args.id_column)
    report = audit_file(args.path, config=config)
    payload = report.to_json() if args.format == "json" else report.to_html() if args.format == "html" else report.to_text()
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
