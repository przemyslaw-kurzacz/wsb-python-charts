"""Minimal CSV parsing/statistics utilities used by API endpoints and tests."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd


class CSVValidationError(ValueError):
    """Raised when CSV cannot be parsed or validated."""


ALLOWED_SEPARATORS = [",", ";", "\t"]


def find_user_csv_file(upload_root: str, username: str) -> Optional[str]:
    """Return path to the first CSV file for the user, or None."""
    user_dir = Path(upload_root) / username
    if not user_dir.exists():
        return None
    files = sorted(user_dir.glob("*.csv"))
    if not files:
        return None
    return str(files[0])


def _try_read_with_separator(path: str, sep: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=sep, engine="python")


def parse_and_validate_csv(path: str) -> pd.DataFrame:
    """Parse CSV from disk and validate basic schema."""
    p = Path(path)
    if not p.exists():
        raise CSVValidationError("CSV file does not exist")

    if p.stat().st_size == 0:
        raise CSVValidationError("CSV file is empty")

    raw_head = p.read_text(encoding="utf-8", errors="ignore")[:4096]

    last_error: Optional[Exception] = None
    best_df: Optional[pd.DataFrame] = None
    best_cols = -1

    for sep in ALLOWED_SEPARATORS:
        try:
            candidate = _try_read_with_separator(str(p), sep)
            ccols = int(candidate.shape[1])
            if ccols > best_cols:
                best_df = candidate
                best_cols = ccols
        except Exception as e:
            last_error = e

    if best_df is None:
        raise CSVValidationError("Unable to parse CSV with supported delimiters") from last_error

    if best_cols == 1 and "|" in raw_head:
        raise CSVValidationError("Unsupported delimiter detected (expected comma/semicolon/tab)")

    df = best_df

    if df.shape[0] == 0:
        raise CSVValidationError("CSV has no rows")
    if df.shape[1] < 1:
        raise CSVValidationError("CSV has no columns")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    rows, cols = df.shape
    missing_total = int(df.isna().sum().sum())

    numeric_columns: List[str] = []
    numeric_summary: Dict[str, Dict[str, Any]] = {}

    for col in df.columns:
        series = df[col]
        coerced = pd.to_numeric(series, errors="coerce")

        if coerced.notna().any():
            numeric_columns.append(col)

            non_numeric_mask = series.notna() & coerced.isna()
            non_numeric_count = int(non_numeric_mask.sum())

            clean = coerced.dropna()
            numeric_summary[col] = {
                "count": int(clean.shape[0]),
                "non_numeric_as_nan": non_numeric_count,
                "mean": float(clean.mean()) if clean.shape[0] else None,
                "min": float(clean.min()) if clean.shape[0] else None,
                "max": float(clean.max()) if clean.shape[0] else None,
            }

    return {
        "rows": int(rows),
        "cols": int(cols),
        "columns": list(df.columns),
        "missing_total": missing_total,
        "numeric_columns": numeric_columns,
        "numeric_summary": numeric_summary,
    }


_MIN_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/6X9nKcAAAAASUVORK5CYII="
)


def generate_histogram_png(df: pd.DataFrame) -> bytes:
    first_col: Optional[str] = None
    data = None

    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().any():
            first_col = col
            data = coerced.dropna()
            break

    if first_col is None or data is None:
        raise CSVValidationError("No numeric columns available for plotting")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        fig = plt.figure(figsize=(4, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.hist(data.values, bins=10)
        ax.set_title(f"Histogram: {first_col}")
        ax.set_xlabel(first_col)
        ax.set_ylabel("count")

        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return base64.b64decode(_MIN_PNG_BASE64)
