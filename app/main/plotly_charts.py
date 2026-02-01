"""app/main/plotly_charts.py

Interaktywne wykresy oparte o Plotly (JSON -> frontend renderuje Plotly.js).

Cel:
- przenieść ciężar "ładnych wykresów" na frontend,
- umożliwić filtry bez przeładowywania strony (fetch -> /api/chart),
- ograniczyć generowanie obrazków (base64) po stronie serwera.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
import json

import pandas as pd
import plotly.express as px
import plotly.io as pio


ChartType = Literal["histogram", "box", "bar_counts", "scatter", "corr_heatmap"]


def _apply_filters(
    df: pd.DataFrame,
    *,
    filter_column: str | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
) -> pd.DataFrame:
    """Minimalny system filtrów:
    - dla kolumn numerycznych: zakres [min, max]
    - dla kategorycznych: lista wartości
    - prosty operator tekstowy: contains/equals (dla string)
    """
    if not filter_column or filter_column not in df.columns:
        return df

    s = df[filter_column]

    # Zakres dla liczb
    if pd.api.types.is_numeric_dtype(s):
        out = df
        if filter_min is not None:
            out = out[out[filter_column] >= filter_min]
        if filter_max is not None:
            out = out[out[filter_column] <= filter_max]
        return out

    # Kategorie
    if filter_values:
        return df[df[filter_column].astype(str).isin([str(v) for v in filter_values])]

    # Tekstowe contains/equals
    if filter_op and filter_value is not None:
        st = s.astype(str)
        val = str(filter_value)
        if filter_op == "contains":
            return df[st.str.contains(val, case=False, na=False)]
        if filter_op == "equals":
            return df[st == val]

    return df


def figure_json(fig) -> dict[str, Any]:
    """Plotly Figure -> dict gotowy do jsonify.

    Używamy plotly.io.to_json() który prawidłowo konwertuje numpy arrays,
    a następnie parsujemy z powrotem do dict.
    """
    json_str = pio.to_json(fig)
    return json.loads(json_str)


def histogram(
    df: pd.DataFrame,
    *,
    column: str,
    bins: int = 30,
    filter_column: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    df_f = _apply_filters(
        df,
        filter_column=filter_column,
        filter_min=filter_min,
        filter_max=filter_max,
        filter_values=filter_values,
        filter_op=filter_op,
        filter_value=filter_value,
    )
    fig = px.histogram(
        df_f,
        x=column,
        nbins=bins,
        title=f"Histogram: {column}",
    )
    fig.update_layout(margin=dict(l=30, r=20, t=55, b=30))
    return figure_json(fig)


def boxplot(
    df: pd.DataFrame,
    *,
    column: str,
    by: str | None = None,
    filter_column: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    df_f = _apply_filters(
        df,
        filter_column=filter_column,
        filter_min=filter_min,
        filter_max=filter_max,
        filter_values=filter_values,
        filter_op=filter_op,
        filter_value=filter_value,
    )
    fig = px.box(
        df_f,
        y=column,
        x=by if by else None,
        points="outliers",
        title=f"Boxplot: {column}" + (f" (grupowanie: {by})" if by else ""),
    )
    fig.update_layout(margin=dict(l=30, r=20, t=55, b=30))
    return figure_json(fig)


def bar_counts(
    df: pd.DataFrame,
    *,
    column: str,
    top_n: int = 20,
    filter_column: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    df_f = _apply_filters(
        df,
        filter_column=filter_column,
        filter_min=filter_min,
        filter_max=filter_max,
        filter_values=filter_values,
        filter_op=filter_op,
        filter_value=filter_value,
    )
    counts = df_f[column].astype(str).value_counts(dropna=False).head(top_n).sort_values(ascending=True)
    cdf = counts.reset_index()
    cdf.columns = [column, "count"]
    fig = px.bar(
        cdf,
        x="count",
        y=column,
        orientation="h",
        title=f"Liczności: {column} (top {top_n})",
    )
    fig.update_layout(margin=dict(l=60, r=20, t=55, b=30))
    return figure_json(fig)


def scatter(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None = None,
    filter_column: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    df_f = _apply_filters(
        df,
        filter_column=filter_column,
        filter_min=filter_min,
        filter_max=filter_max,
        filter_values=filter_values,
        filter_op=filter_op,
        filter_value=filter_value,
    )
    fig = px.scatter(
        df_f,
        x=x,
        y=y,
        color=color if color else None,
        title=f"Wykres punktowy: {x} vs {y}",
    )
    fig.update_layout(margin=dict(l=30, r=20, t=55, b=30))
    return figure_json(fig)


def corr_heatmap(df: pd.DataFrame) -> dict[str, Any] | None:
    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        return None
    corr = num.corr()
    fig = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        title="Korelacje (numeryczne)",
    )
    fig.update_layout(margin=dict(l=30, r=20, t=55, b=30))
    return figure_json(fig)
