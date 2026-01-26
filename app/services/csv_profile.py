from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import csv
import pandas as pd


# ----------------------------
# Configuration
# ----------------------------

DEFAULT_PREVIEW_ROWS = 50
DEFAULT_SAMPLE_VALUES = 20
MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MB safety limit (adjust as needed)


# ----------------------------
# Helpers
# ----------------------------

def _read_bytes(file_obj) -> bytes:
    """
    Accepts Flask's FileStorage or a file-like object.
    Reads into memory once to enable sniffing and multiple passes.
    """
    data = file_obj.read()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"File too large ({len(data)} bytes). Limit is {MAX_FILE_BYTES} bytes.")
    return data


def _detect_encoding(data: bytes) -> str:
    """
    Prefer UTF-8 with BOM (common for Polish public datasets), then UTF-8, then fallback to cp1250.
    You can extend this if needed.
    """
    # UTF-8 with BOM
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    # Try UTF-8
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # Common Windows Polish encoding (legacy)
        return "cp1250"


def _detect_delimiter(text_sample: str) -> str:
    """
    Use csv.Sniffer if possible; fallback to common delimiters.
    """
    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        # Heuristic fallback: choose the delimiter that appears most in the first non-empty line
        lines = [ln for ln in text_sample.splitlines() if ln.strip()]
        if not lines:
            return ","
        first = lines[0]
        candidates = [",", ";", "\t", "|"]
        return max(candidates, key=lambda d: first.count(d))


def _has_header(text_sample: str) -> bool:
    try:
        return csv.Sniffer().has_header(text_sample)
    except Exception:
        return True  # default: assume header exists


def _is_probably_code_series(s: pd.Series) -> bool:
    """
    Decide if a column should be treated as 'code-like' categorical string rather than numeric:
    - if any value has leading zeros (e.g., "02")
    - or if all non-null values are digits and length is small/fixed-ish (typical codes)
    """
    non_null = s.dropna().astype(str).str.strip()
    if non_null.empty:
        return False

    # Leading zeros anywhere
    if (non_null.str.len() >= 2).any():
        if (non_null.str.match(r"^0\d+$")).any():
            return True

    # All digits and short => code-like (e.g., 1..5, 01..99 etc.)
    if non_null.str.match(r"^\d+$").all():
        lengths = non_null.str.len()
        if lengths.max() <= 6 and (lengths.nunique() <= 3):
            return True

    return False


def _try_parse_datetime(s: pd.Series) -> Tuple[Optional[pd.Series], float]:
    """
    Attempt datetime parsing and return (parsed_series, success_ratio).
    """
    non_null = s.dropna().astype(str).str.strip()
    if non_null.empty:
        return None, 0.0

    # Try ISO-like first, then day-first
    parsed1 = pd.to_datetime(non_null, errors="coerce", utc=False)
    success1 = parsed1.notna().mean()

    parsed2 = pd.to_datetime(non_null, errors="coerce", dayfirst=True, utc=False)
    success2 = parsed2.notna().mean()

    if max(success1, success2) < 0.9:
        return None, max(success1, success2)

    best = parsed1 if success1 >= success2 else parsed2

    # Re-align to original index
    aligned = pd.Series(pd.NaT, index=s.index)
    aligned.loc[non_null.index] = best
    return aligned, max(success1, success2)


def _try_parse_numeric(s: pd.Series) -> Tuple[Optional[pd.Series], float]:
    """
    Attempt numeric parsing. Handles comma decimal.
    Returns (parsed_series, success_ratio).
    """
    non_null = s.dropna().astype(str).str.strip()
    if non_null.empty:
        return None, 0.0

    # Normalize decimal comma, remove spaces
    normalized = non_null.str.replace(" ", "", regex=False).str.replace(",", ".", regex=False)

    parsed = pd.to_numeric(normalized, errors="coerce")
    success = parsed.notna().mean()

    if success < 0.9:
        return None, success

    aligned = pd.Series(pd.NA, index=s.index, dtype="Float64")
    aligned.loc[non_null.index] = parsed.astype("Float64")
    return aligned, success


def _json_safe_value(v: Any) -> Any:
    if pd.isna(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        # ISO for frontend
        return v.isoformat()
    return v


# ----------------------------
# Core profiler
# ----------------------------

@dataclass
class CsvProfileResult:
    meta: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    schema: Dict[str, Any]
    preview: Dict[str, Any]


def profile_csv_upload(file_obj, preview_rows: int = DEFAULT_PREVIEW_ROWS) -> CsvProfileResult:
    """
    Main entry point for Flask upload handling.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        data = _read_bytes(file_obj)
    except Exception as e:
        return CsvProfileResult(
            meta={},
            errors=[str(e)],
            warnings=[],
            schema={"columns": [], "suggestions": {"dimensions": [], "measures": [], "datetimes": []}},
            preview={"rows": [], "limit": preview_rows},
        )

    encoding = _detect_encoding(data)

    # Decode a sample for delimiter sniffing
    try:
        text = data.decode(encoding, errors="replace")
    except Exception as e:
        return CsvProfileResult(
            meta={},
            errors=[f"Failed to decode file with encoding {encoding}: {e}"],
            warnings=[],
            schema={"columns": [], "suggestions": {"dimensions": [], "measures": [], "datetimes": []}},
            preview={"rows": [], "limit": preview_rows},
        )

    sample = "\n".join(text.splitlines()[:50])
    delimiter = _detect_delimiter(sample)
    header_present = _has_header(sample)

    if not header_present:
        errors.append("CSV appears to have no header row. A header is required for charting.")
        return CsvProfileResult(
            meta={"encoding": encoding, "delimiter": delimiter, "header": False},
            errors=errors,
            warnings=warnings,
            schema={"columns": [], "suggestions": {"dimensions": [], "measures": [], "datetimes": []}},
            preview={"rows": [], "limit": preview_rows},
        )

    # Load using pandas
    # Use dtype=str initially to avoid losing leading zeros and to enable robust inference ourselves.
    try:
        df = pd.read_csv(
            BytesIO(data),
            encoding=encoding,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,  # treat empty as empty string; we normalize below
        )
    except Exception as e:
        errors.append(f"Failed to parse CSV: {e}")
        return CsvProfileResult(
            meta={"encoding": encoding, "delimiter": delimiter, "header": True},
            errors=errors,
            warnings=warnings,
            schema={"columns": [], "suggestions": {"dimensions": [], "measures": [], "datetimes": []}},
            preview={"rows": [], "limit": preview_rows},
        )

    # Normalize empty strings -> NA
    df = df.applymap(lambda x: pd.NA if (x is None or (isinstance(x, str) and x.strip() == "")) else x)

    if df.shape[1] == 0:
        errors.append("CSV contains zero columns after parsing.")
    if df.shape[0] == 0:
        errors.append("CSV contains zero rows after parsing.")

    # Duplicate columns
    cols = list(df.columns)
    if len(set(cols)) != len(cols):
        warnings.append("CSV has duplicate column names. This can break charting; rename duplicates.")
        # Make columns unique defensively
        seen = {}
        new_cols = []
        for c in cols:
            if c not in seen:
                seen[c] = 1
                new_cols.append(c)
            else:
                seen[c] += 1
                new_cols.append(f"{c}__{seen[c]}")
        df.columns = new_cols

    if errors:
        return CsvProfileResult(
            meta={"encoding": encoding, "delimiter": delimiter, "header": True, "rows": int(df.shape[0]), "cols": int(df.shape[1])},
            errors=errors,
            warnings=warnings,
            schema={"columns": [], "suggestions": {"dimensions": [], "measures": [], "datetimes": []}},
            preview={"rows": [], "limit": preview_rows},
        )

    # Type inference per column
    schema_cols: List[Dict[str, Any]] = []
    dimensions: List[str] = []
    measures: List[str] = []
    datetimes: List[str] = []

    for col in df.columns:
        s = df[col]
        missing_count = int(s.isna().sum())
        non_missing = s.dropna().astype(str).str.strip()
        unique_count = int(non_missing.nunique())

        inferred_type = "string"
        semantic_type = "categorical"
        stats: Optional[Dict[str, Any]] = None

        # Code-like columns should stay categorical strings
        if _is_probably_code_series(s):
            inferred_type = "string"
            semantic_type = "categorical"
            dimensions.append(col)
        else:
            # Try datetime
            parsed_dt, dt_ratio = _try_parse_datetime(s)
            if parsed_dt is not None:
                inferred_type = "date"
                semantic_type = "datetime"
                datetimes.append(col)
                # Keep parsed values (optional: store back)
                # df[col] = parsed_dt
                mn = parsed_dt.min()
                mx = parsed_dt.max()
                stats = {
                    "min": None if pd.isna(mn) else mn.date().isoformat(),
                    "max": None if pd.isna(mx) else mx.date().isoformat(),
                    "parse_success_ratio": float(dt_ratio),
                }
            else:
                # Try numeric
                parsed_num, num_ratio = _try_parse_numeric(s)
                if parsed_num is not None:
                    inferred_type = "number"
                    semantic_type = "measure"
                    measures.append(col)
                    # df[col] = parsed_num
                    stats = {
                        "min": float(parsed_num.min()) if parsed_num.notna().any() else None,
                        "max": float(parsed_num.max()) if parsed_num.notna().any() else None,
                        "mean": float(parsed_num.mean()) if parsed_num.notna().any() else None,
                        "parse_success_ratio": float(num_ratio),
                    }
                else:
                    # Default: categorical if low-ish unique; else string dimension
                    inferred_type = "string"
                    semantic_type = "categorical"
                    dimensions.append(col)

        sample_values = (
            non_missing.drop_duplicates().head(DEFAULT_SAMPLE_VALUES).tolist()
            if not non_missing.empty
            else []
        )

        schema_cols.append(
            {
                "name": col,
                "inferred_type": inferred_type,      # string | number | date
                "semantic_type": semantic_type,      # categorical | measure | datetime
                "nullable": missing_count > 0,
                "unique_count": unique_count,
                "missing_count": missing_count,
                "sample_values": sample_values,
                "stats": stats,
            }
        )

    # Preview rows (JSON-safe)
    preview_df = df.head(preview_rows)
    preview_rows_list = []
    for _, row in preview_df.iterrows():
        preview_rows_list.append({c: _json_safe_value(row[c]) for c in preview_df.columns})

    meta = {
        "encoding": encoding,
        "delimiter": delimiter,
        "header": True,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "preview_rows": int(min(preview_rows, df.shape[0])),
    }

    schema = {
        "columns": schema_cols,
        "suggestions": {
            "dimensions": dimensions,
            "measures": measures,
            "datetimes": datetimes,
        },
    }

    return CsvProfileResult(
        meta=meta,
        errors=[],
        warnings=warnings,
        schema=schema,
        preview={"rows": preview_rows_list, "limit": preview_rows},
    )
