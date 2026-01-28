"""app/main/charts.py

Ten moduł trzyma wyłącznie logikę tworzenia wykresów.

Dlaczego osobny plik?
- routes.py ma być prosty (obsługa widoków),
- tutaj trzymamy "czystą" logikę wizualizacji,
- łatwo to później testować / rozwijać.
"""

from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Krok 0: ustawienie podstawowej estetyki dla seaborn/matplotlib
# Dzięki temu wykresy wyglądają czytelnie "z automatu".
sns.set_theme(style="whitegrid", context="notebook")




def _fig_to_base64(fig: plt.Figure) -> str:
    """Zamienia wykres (matplotlib Figure) na base64 string.

    Dzięki temu możemy w HTML zrobić:
    <img src="data:image/png;base64, ... ">
    """
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=160)

    buffer.seek(0)
    image_b64 = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close(fig)
    return image_b64


def create_histogram(df: pd.DataFrame, column: str) -> str:
    """Histogram dla kolumny numerycznej."""
    fig, ax = plt.subplots(figsize=(7, 4))

    # Krok 1: rysujemy histogram + opcjonalnie KDE (gładka linia)
    sns.histplot(df[column].dropna(), kde=True, ax=ax)

    # Krok 2: opisy (ważne dla czytelności!)
    ax.set_title(f"Histogram wartości: {column}")
    ax.set_xlabel(column)
    ax.set_ylabel("Liczność")

    return _fig_to_base64(fig)

def create_boxplot(df: pd.DataFrame, column: str) -> str:
    """Ulepszony boxplot:
    - pionowy boxplot
    - punkty (stripplot), żeby było widać rozkład
    - większa figura
    """
    data = df[column].dropna()

    fig, ax = plt.subplots(figsize=(6, 6))

    # Krok 1: boxplot (bez "fliers", bo punkty pokażemy sami)
    sns.boxplot(y=data, ax=ax, showfliers=False)

    # Krok 2: punkty z lekką losowością (jitter), żeby się nie nakładały
    sns.stripplot(y=data, ax=ax, jitter=0.25, size=3, alpha=0.35)

    # Krok 3: opisy
    ax.set_title(f"Boxplot + punkty: {column}")
    ax.set_ylabel(column)

    # Krok 4 (opcjonalnie): delikatna siatka
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)

        # Krok 5: Zoom na środkowe 50% (IQR) + margines
    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr = q3 - q1

    if iqr > 0:
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        ax.set_ylim(lower, upper)


    return _fig_to_base64(fig)




def create_barplot_counts(df: pd.DataFrame, column: str, top_n: int = 15) -> str:
    """Barplot liczności dla kolumny kategorycznej (POZIOMY = czytelniejszy).

    Dlaczego poziomy?
    - długie etykiety nie nachodzą na siebie,
    - wykres lepiej wygląda na telefonie.
    """
    # Krok 1: policz wartości (wraz z NaN jako osobną kategorią)
    counts = df[column].astype(str).value_counts(dropna=False)

    # Krok 2: ogranicz liczbę kategorii (czytelność)
    counts = counts.head(top_n)

    # Krok 3: rysujemy poziomo -> barh
    fig, ax = plt.subplots(figsize=(9, 6))
    counts.sort_values().plot(kind="barh", ax=ax)

    ax.set_title(f"Liczności kategorii: {column} (top {top_n})")
    ax.set_xlabel("Liczba wystąpień")
    ax.set_ylabel(column)

    # Krok 4: dodaj wartości na słupkach (czytelność)
    for i, v in enumerate(counts.sort_values().values):
        ax.text(v, i, f" {int(v)}", va="center")

    return _fig_to_base64(fig)

def create_correlation_heatmap(df: pd.DataFrame) -> str | None:
    """
    Heatmapa korelacji dla kolumn numerycznych.
    Jeśli nie ma sensownej liczby kolumn – zwracamy None.
    """
    numeric_df = df.select_dtypes(include="number")

    # Musimy mieć przynajmniej 2 kolumny
    if numeric_df.shape[1] < 2:
        return None

    corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(8, 6))

    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        ax=ax
    )

    ax.set_title("Heatmapa korelacji zmiennych numerycznych")

    return _fig_to_base64(fig)
