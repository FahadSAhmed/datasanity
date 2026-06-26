from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import re
import numpy as np
import pandas as pd
from ._shared import Issue, Report, load_table


@dataclass
class DataSanityConfig:
    missingness_threshold: float = 0.30
    high_cardinality_threshold: float = 0.80
    infer_id_columns: bool = True
    id_columns: list[str] = field(default_factory=list)
    max_examples: int = 5


def _examples(values, n: int = 5):
    out = []
    for v in list(values)[:n]:
        if pd.isna(v):
            out.append(None)
        else:
            out.append(v.item() if hasattr(v, "item") else v)
    return out


def _is_id_col(col: str) -> bool:
    low = col.strip().lower()
    return low in {"id", "patient_id", "sample_id", "case_id", "mrn", "accession"} or low.endswith("_id")


def _date_like(col: str) -> bool:
    return any(token in col.lower() for token in ["date", "dob", "time", "timestamp"])


def _numeric_checks(df: pd.DataFrame, config: DataSanityConfig) -> list[Issue]:
    issues: list[Issue] = []
    for col in df.columns:
        s = df[col]
        if not pd.api.types.is_numeric_dtype(s):
            continue
        nonnull = s.dropna()
        if nonnull.empty:
            continue
        low = col.lower()
        if "age" in low:
            bad = nonnull[(nonnull < 0) | (nonnull > 120)]
            if not bad.empty:
                issues.append(Issue("datasanity", "numeric_range", "error", "Age-like column contains values outside 0-120.", col, len(bad), _examples(bad, config.max_examples)))
        if any(tok in low for tok in ["percent", "percentage", "pct", "%"]):
            bad = nonnull[(nonnull < 0) | (nonnull > 100)]
            if not bad.empty:
                issues.append(Issue("datasanity", "numeric_range", "warning", "Percentage-like column contains values outside 0-100.", col, len(bad), _examples(bad, config.max_examples)))
        if any(tok in low for tok in ["count", "cell", "wbc", "hgb", "platelet", "creatinine", "height", "weight"]):
            bad = nonnull[nonnull < 0]
            if not bad.empty:
                issues.append(Issue("datasanity", "negative_values", "warning", "Nonnegative-looking column contains negative values.", col, len(bad), _examples(bad, config.max_examples)))
        q1, q3 = nonnull.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            lb, ub = q1 - 3 * iqr, q3 + 3 * iqr
            bad = nonnull[(nonnull < lb) | (nonnull > ub)]
            if len(bad) >= max(3, int(0.01 * len(nonnull))):
                issues.append(Issue("datasanity", "outlier_iqr", "info", "Column has values beyond 3x IQR fences.", col, len(bad), _examples(bad, config.max_examples)))
    return issues


def _missingness_checks(df: pd.DataFrame, config: DataSanityConfig) -> list[Issue]:
    issues: list[Issue] = []
    for col in df.columns:
        n = int(df[col].isna().sum())
        frac = n / len(df) if len(df) else 0
        if frac >= config.missingness_threshold and n > 0:
            issues.append(Issue("datasanity", "missingness", "warning", f"Column missingness is {frac:.1%}, above threshold {config.missingness_threshold:.0%}.", col, n))
    empty_rows = int(df.isna().all(axis=1).sum()) if len(df) else 0
    if empty_rows:
        issues.append(Issue("datasanity", "empty_rows", "warning", "Rows with all values missing detected.", None, empty_rows))
    return issues


def _duplicate_checks(df: pd.DataFrame, config: DataSanityConfig) -> list[Issue]:
    issues: list[Issue] = []
    dup_rows = int(df.duplicated().sum())
    if dup_rows:
        issues.append(Issue("datasanity", "duplicate_rows", "warning", "Fully duplicated rows detected.", None, dup_rows))
    id_cols = list(config.id_columns)
    if config.infer_id_columns:
        id_cols.extend([c for c in df.columns if _is_id_col(str(c)) and c not in id_cols])
    for col in id_cols:
        if col not in df.columns:
            continue
        duplicated = df[col].dropna()[df[col].dropna().duplicated(keep=False)]
        if not duplicated.empty:
            issues.append(Issue("datasanity", "duplicate_ids", "error", "Duplicate non-null identifiers detected.", col, len(duplicated), _examples(pd.unique(duplicated), config.max_examples)))
    return issues


def _category_checks(df: pd.DataFrame, config: DataSanityConfig) -> list[Issue]:
    issues: list[Issue] = []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            continue
        nonnull = s.dropna().astype(str)
        if nonnull.empty:
            continue
        normalized = nonnull.str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
        raw_unique = nonnull.nunique(dropna=True)
        norm_unique = normalized.nunique(dropna=True)
        if norm_unique < raw_unique:
            issues.append(Issue("datasanity", "mixed_categories", "warning", "Category labels differ only by case/spacing.", col, raw_unique - norm_unique, _examples(nonnull.unique(), config.max_examples)))
        unique_frac = raw_unique / len(nonnull)
        if unique_frac >= config.high_cardinality_threshold and len(nonnull) >= 20:
            issues.append(Issue("datasanity", "high_cardinality", "info", f"Text column has high cardinality ({unique_frac:.1%}); confirm it is not an identifier.", col, raw_unique, _examples(nonnull.unique(), config.max_examples)))
    return issues


def _date_checks(df: pd.DataFrame, config: DataSanityConfig) -> list[Issue]:
    issues: list[Issue] = []
    for col in df.columns:
        if not _date_like(str(col)):
            continue
        s = df[col].dropna()
        if s.empty or pd.api.types.is_datetime64_any_dtype(s):
            continue
        parsed = pd.to_datetime(s, errors="coerce")
        bad = s[parsed.isna()]
        if not bad.empty:
            issues.append(Issue("datasanity", "invalid_dates", "warning", "Date-like column contains unparsable values.", col, len(bad), _examples(bad, config.max_examples)))
    return issues


def _constant_checks(df: pd.DataFrame) -> list[Issue]:
    issues = []
    for col in df.columns:
        if df[col].nunique(dropna=True) <= 1 and len(df) > 1:
            issues.append(Issue("datasanity", "constant_column", "info", "Column has zero or near-zero observed variability.", col, int(df[col].notna().sum())))
    return issues


def audit_dataframe(df: pd.DataFrame, config: DataSanityConfig | None = None, dataset_name: str = "DataFrame") -> Report:
    """Run data sanity checks against a DataFrame."""
    config = config or DataSanityConfig()
    issues: list[Issue] = []
    for check in [_missingness_checks, _duplicate_checks, _numeric_checks, _category_checks, _date_checks]:
        issues.extend(check(df, config))
    issues.extend(_constant_checks(df))
    summary = {
        "dataset": dataset_name,
        "rows": len(df),
        "columns": len(df.columns),
        "issues": len(issues),
        "missing_cells": int(df.isna().sum().sum()),
    }
    return Report("DataSanity report", summary, issues)


def audit_file(path: str | Path, config: DataSanityConfig | None = None) -> Report:
    df = load_table(path)
    return audit_dataframe(df, config=config, dataset_name=str(path))
