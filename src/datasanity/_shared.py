from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import pandas as pd


@dataclass(frozen=True)
class Issue:
    """A structured issue reported by a package check."""

    package: str
    check: str
    severity: str
    message: str
    column: str | None = None
    count: int | None = None
    examples: list[Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    """A small serializable report object."""

    title: str
    summary: dict[str, Any]
    issues: list[Issue]

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "summary": self.summary, "issues": [i.to_dict() for i in self.issues]}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_text(self) -> str:
        lines = [self.title, "=" * len(self.title), ""]
        for k, v in self.summary.items():
            lines.append(f"{k}: {v}")
        lines.append("")
        if not self.issues:
            lines.append("No issues detected.")
            return "\n".join(lines)
        lines.append("Issues:")
        for i, issue in enumerate(self.issues, start=1):
            col = f" [{issue.column}]" if issue.column else ""
            cnt = f" count={issue.count}" if issue.count is not None else ""
            lines.append(f"{i}. {issue.severity.upper()} {issue.check}{col}:{cnt} {issue.message}")
            if issue.examples:
                lines.append(f"   examples: {issue.examples[:5]}")
        return "\n".join(lines)

    def to_html(self) -> str:
        rows = []
        for issue in self.issues:
            rows.append(
                "<tr>"
                f"<td>{issue.severity}</td>"
                f"<td>{issue.check}</td>"
                f"<td>{issue.column or ''}</td>"
                f"<td>{issue.count if issue.count is not None else ''}</td>"
                f"<td>{issue.message}</td>"
                f"<td>{issue.examples or ''}</td>"
                "</tr>"
            )
        summary_items = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in self.summary.items())
        return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{self.title}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:2rem auto;}}table{{border-collapse:collapse;width:100%;}}td,th{{border:1px solid #ccc;padding:0.4rem;vertical-align:top;}}th{{background:#f5f5f5;}}</style>
</head><body><h1>{self.title}</h1><ul>{summary_items}</ul>
<table><thead><tr><th>Severity</th><th>Check</th><th>Column</th><th>Count</th><th>Message</th><th>Examples</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""


def load_table(path: str | Path, sheet_name: str | int | None = 0) -> pd.DataFrame:
    """Load a CSV, TSV, or Excel table into a DataFrame."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(p, sep="\t")
    if suffix in {".xls", ".xlsx", ".xlsm"}:
        return pd.read_excel(p, sheet_name=sheet_name)
    raise ValueError(f"Unsupported table format: {suffix}")


def write_json(obj, path: str | Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
