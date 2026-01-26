"""Minimal CSV parsing/statistics utilities used by API endpoints and tests."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd


class CSVValidationError(ValueError):
    """Raised when CSV cannot be parsed or validated."""


ALLOWED_SEPARATORS = [",", ";", "\t"]


def find_user_csv_file(upload_folder: str, username: str) -> Optional[str]:
    """Find first CSV file for a user in uploads folder."""
    user_dir = Path(upload_folder) / username
    if not user_dir.exists():
        return None

    csvs = list(user_dir.glob("*.csv"))
    if not csvs:
        return None

    return str(csvs[0])


def _try_read_with_separator(path: str, sep: str) -> pd.DataFrame:
    """Try read CSV with a given separator."""
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
            tmp = _try_read_with_separator(path, sep)
            ccols = tmp.shape[1]
            if ccols > best_cols:
                best_df = tmp
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

            numeric_summary[col] = {
                "min": float(coerced.min()),
                "max": float(coerced.max()),
                "mean": float(coerced.mean()),
                "missing": int(coerced.isna().sum()),
                "non_numeric": non_numeric_count,
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
    """Generate a histogram PNG for first numeric-like column, fallback to 1x1 PNG."""
    import io
    import matplotlib.pyplot as plt

    # Find first column with any numeric coercion
    first_col = None
    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().any():
            first_col = col
            data = coerced.dropna()
            break

    if first_col is None:
        return base64.b64decode(_MIN_PNG_BASE64)

    try:
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


def basic_prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Proste przygotowanie danych do wizualizacji.

    Co robimy:
    - próbujemy skonwertować tekstowe kolumny na liczby (np. '10', '10.5', '10,5')
    - uzupełniamy braki danych:
        - liczby -> medianą
        - tekst -> 'Brak danych'

    To jest celowo proste i "junior-friendly".
    """
    df = df.copy()

    # Krok 1: spróbuj konwersji kolumn tekstowych na liczby
    for col in df.columns:
        if df[col].dtype == "object":
            # Ujednolicamy spacje i puste wartości
            series_str = df[col].astype(str).str.strip()
            series_str = series_str.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

            # Próba konwersji na liczbę (obsługa liczb z przecinkiem)
            numeric_candidate = series_str.str.replace(",", ".", regex=False)
            converted = pd.to_numeric(numeric_candidate, errors="coerce")

            # Jeśli większość wartości da się zamienić na liczbę -> traktujemy jako kolumnę numeryczną
            ratio_ok = converted.notna().mean()
            if ratio_ok >= 0.8:
                df[col] = converted
            else:
                df[col] = series_str  # zostawiamy jako tekst

    # Krok 2: uzupełnianie braków danych
    numeric_cols = df.select_dtypes(include="number").columns
    categorical_cols = df.select_dtypes(exclude="number").columns

    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())

    for col in categorical_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna("Brak danych")

    return df


def detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Wybiera kolumny do wykresów (automatycznie).

    Zwracamy:
    - 1 kolumnę numeryczną (histogram + boxplot)
    - 1 kolumnę kategoryczną (barplot)

    Jeśli nie ma sensownych kolumn -> zwracamy None.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    numeric_col = numeric_cols[0] if numeric_cols else None

    # Dla kategorii unikamy kolumn typu 'id' (często mają milion unikalnych wartości)
    categorical_col = None
    for col in categorical_cols:
        unique_ratio = df[col].nunique(dropna=False) / max(len(df), 1)
        if unique_ratio < 0.5:  # prosta heurystyka: nie bierz prawie-unikalnych kolumn
            categorical_col = col
            break

    # Jeśli nie znaleźliśmy "dobrej" kategorycznej -> weź pierwszą
    if categorical_col is None and categorical_cols:
        categorical_col = categorical_cols[0]

    return numeric_col, categorical_col
