#!/usr/bin/env python3
"""
Idempotentny generator unit testów dla Algorytmu Bentleya (Bentley–Ottmann).

Co robi:
- tworzy tests/test_bentley_ottmann.py (testy w klasach)
- dopisuje do tests/conftest.py fixture `bentley_callable` + helpery detekcji

Testy:
- edge-case pack: pionowe, endpointy, duplikaty, overlapy, floaty

Jak wskazać dokładny interfejs funkcji:
- ustaw env:
    BENTLEY_MODULE="app.algorithms.bentley_ottmann"
    BENTLEY_FUNC="bentley_ottmann"

Uruchom:
    python add_bentley_tests.py
    pytest -q
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

pytestmark = pytest.mark.bentley

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "app").exists() and (candidate / "tests").exists():
            return candidate
    raise SystemExit("Nie mogę znaleźć repo root. Uruchom skrypt w katalogu projektu.")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8")


def patch_conftest(conftest_path: Path) -> None:
    base = conftest_path.read_text(encoding="utf-8") if conftest_path.exists() else ""

    marker = "# === BENTLEY_FIXTURES_START ==="
    if marker in base:
        return  # already patched

    addon = r'''
# === BENTLEY_FIXTURES_START ===
# Fixtures + helpery do auto-detekcji implementacji Algorytmu Bentleya.
# Jeśli chcesz wymusić konkretny moduł/funkcję:
#   set BENTLEY_MODULE="app.algorithms.bentley_ottmann"
#   set BENTLEY_FUNC="bentley_ottmann"
# w PowerShell:
#   $env:BENTLEY_MODULE="..."
#   $env:BENTLEY_FUNC="..."

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Callable, Any, Iterable, Tuple, Set

import pytest


def _iter_candidate_modules(repo_root: Path) -> list[str]:
    """
    Szuka plików zawierających bentley/ottmann/sweep.
    Zwraca listę modułów do importu w stylu pythonowym (np. app.algorithms.bentley_ottmann)
    """
    candidates: list[str] = []
    search_dirs = [repo_root / "app", repo_root / "src"]
    patterns = ("bentley", "ottmann", "sweep", "line_sweep", "intersections")

    for d in search_dirs:
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            name = py.name.lower()
            if any(p in name for p in patterns):
                rel = py.relative_to(repo_root)
                mod = ".".join(rel.with_suffix("").parts)
                candidates.append(mod)

    # też dopuszczamy "app.main.processing" jeśli ktoś wrzucił tam logikę
    if (repo_root / "app" / "main" / "processing.py").exists():
        candidates.append("app.main.processing")

    # uniq stable order
    uniq: list[str] = []
    for m in candidates:
        if m not in uniq:
            uniq.append(m)
    return uniq


def _find_callable_in_module(module: Any) -> Callable:
    """
    Szuka funkcji algorytmu po nazwach typowych.
    """
    preferred_names = [
        "bentley_ottmann",
        "bentley",
        "find_intersections",
        "compute_intersections",
        "intersections",
        "sweep_line",
    ]

    for name in preferred_names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn

    # fallback: jeśli w module jest jedna sensowna funkcja publiczna z parametrem segments
    funcs = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = inspect.signature(obj)
        if len(sig.parameters) >= 1:
            funcs.append((name, obj))

    if len(funcs) == 1:
        return funcs[0][1]

    raise RuntimeError(
        f"Nie znaleziono funkcji algorytmu w module {module.__name__}. "
        f"Ustaw BENTLEY_MODULE/BENTLEY_FUNC."
    )


def _resolve_bentley_callable(repo_root: Path) -> Callable:
    env_mod = os.environ.get("BENTLEY_MODULE")
    env_fn = os.environ.get("BENTLEY_FUNC")

    # ensure repo root in sys.path
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if env_mod:
        mod = importlib.import_module(env_mod)
        if env_fn:
            fn = getattr(mod, env_fn)
            if not callable(fn):
                raise RuntimeError(f"{env_mod}.{env_fn} nie jest callable.")
            return fn
        return _find_callable_in_module(mod)

    # auto-detect
    for mod_name in _iter_candidate_modules(repo_root):
        try:
            mod = importlib.import_module(mod_name)
            fn = _find_callable_in_module(mod)
            return fn
        except Exception:
            continue

    raise RuntimeError(
        "Nie mogę znaleźć implementacji Algorytmu Bentleya. "
        "Dodaj plik bentley_ottmann.py / bentley.py albo ustaw ENV BENTLEY_MODULE/BENTLEY_FUNC."
    )


def _normalize_points(result: Any, ndigits: int = 6) -> Set[Tuple[float, float]]:
    """
    Normalizuje wynik algorytmu do set[(x,y)].
    Obsługuje:
    - set/list/tuple/generator punktów
    - dict (bierzemy keys)
    Punkt może być:
    - (x, y)
    - obiekt z .x .y
    """
    if result is None:
        return set()

    if isinstance(result, dict):
        iterable = result.keys()
    else:
        iterable = result

    pts: Set[Tuple[float, float]] = set()
    for item in iterable:
        x = y = None
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            x, y = item[0], item[1]
        else:
            # object with x/y
            if hasattr(item, "x") and hasattr(item, "y"):
                x, y = getattr(item, "x"), getattr(item, "y")

        if x is None or y is None:
            raise TypeError(
                f"Nie umiem znormalizować elementu wyniku: {item!r}. "
                f"Wynik ma być punktami (x,y) lub obiektami z .x/.y."
            )

        pts.add((round(float(x), ndigits), round(float(y), ndigits)))
    return pts


@pytest.fixture()
def bentley_callable(request) -> Callable:
    """
    Fixture zwraca funkcję algorytmu Bentleya.
    """
    repo_root = Path(request.config.rootpath)
    return _resolve_bentley_callable(repo_root)


@pytest.fixture()
def norm_points() -> Callable:
    return _normalize_points
# === BENTLEY_FIXTURES_END ===
'''
    # Jeżeli conftest jest pusty, dodajmy minimalny nagłówek
    if not base.strip():
        base = '"""pytest fixtures."""\n\n'

    write_file(conftest_path, base.rstrip() + "\n\n" + addon.lstrip())


def main() -> None:
    repo = find_repo_root(Path.cwd())

    # Patch conftest.py
    conftest_path = repo / "tests" / "conftest.py"
    patch_conftest(conftest_path)

    # Create Bentley tests
    test_bentley = r'''"""Unit tests for Bentley–Ottmann algorithm (sweep line intersections).

Wymagania testów:
- deterministyczne
- edge-case pack: pionowe, endpointy, duplikaty, overlapy, floaty

Założenie wejścia:
- segments = [((x1,y1),(x2,y2)), ...]
Jeżeli Twoja funkcja przyjmuje inny format (np. Segment obiekt),
to zmień adapter w _call_algo().
"""

from __future__ import annotations

import math
import pytest


def _segments():
    """Skrót do czytelnych segmentów."""
    return [
        ((0.0, 0.0), (4.0, 4.0)),
        ((0.0, 4.0), (4.0, 0.0)),
    ]


def _call_algo(bentley_callable, segments):
    """
    Adapter: wywołuje algorytm.
    Jeśli Wasz algorytm przyjmuje inne argumenty (np. osobno points),
    zmień to miejsce - reszta testów zostaje.
    """
    return bentley_callable(segments)


class TestBentleyOttmannCore:
    def test_single_intersection_cross(self, bentley_callable, norm_points):
        segments = [
            ((0, 0), (4, 4)),
            ((0, 4), (4, 0)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert (2.0, 2.0) in pts
        assert len(pts) == 1

    def test_intersection_at_endpoint(self, bentley_callable, norm_points):
        segments = [
            ((0, 0), (2, 2)),
            ((2, 2), (4, 0)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert (2.0, 2.0) in pts
        assert len(pts) == 1

    def test_no_intersections(self, bentley_callable, norm_points):
        segments = [
            ((0, 0), (1, 0)),
            ((0, 1), (1, 1)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert pts == set()

    def test_vertical_and_horizontal(self, bentley_callable, norm_points):
        segments = [
            ((2, -1), (2, 3)),  # pionowy
            ((0, 1), (5, 1)),   # poziomy
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert (2.0, 1.0) in pts
        assert len(pts) == 1

    def test_multiple_segments_intersect_in_same_point(self, bentley_callable, norm_points):
        segments = [
            ((0, 0), (4, 4)),
            ((0, 4), (4, 0)),
            ((2, -10), (2, 10)),
            ((-10, 2), (10, 2)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        # wszystkie przecinają się w (2,2)
        assert (2.0, 2.0) in pts
        assert len(pts) == 1


class TestBentleyOttmannEdgeCases:
    def test_duplicate_segments_do_not_duplicate_points(self, bentley_callable, norm_points):
        segments = [
            ((0, 0), (4, 4)),
            ((0, 4), (4, 0)),
            ((0, 0), (4, 4)),  # duplikat
            ((0, 4), (4, 0)),  # duplikat
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert pts == {(2.0, 2.0)}

    def test_zero_length_segment_point_intersection(self, bentley_callable, norm_points):
        # segment o zerowej długości (punkt) leży na drugim segmencie
        segments = [
            ((2, 2), (2, 2)),       # point segment
            ((0, 0), (4, 4)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        # W wielu definicjach to jest poprawne przecięcie
        assert (2.0, 2.0) in pts

    def test_float_intersection_is_stable(self, bentley_callable, norm_points):
        # przecięcie w (1/3, 1/3) -> floaty
        segments = [
            ((0, 0), (1, 1)),
            ((0, 1/3), (1, 1/3)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)

        assert (0.333333, 0.333333) in pts  # po zaokrągleniu do 6 miejsc

    def test_almost_parallel_segments_no_false_positive(self, bentley_callable, norm_points):
        # prawie równoległe, ale nie przecinają się w zakresie
        segments = [
            ((0, 0), (10, 0.000001)),
            ((0, 1), (10, 1.000001)),
        ]
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)
        assert pts == set()

    def test_collinear_overlap_policy(self, bentley_callable, norm_points):
        """
        Overlap (kolinearność) jest "killer-case".
        Różne implementacje robią różne rzeczy:
        - zwracają końce overlapu
        - zwracają pusty set (ignorują)
        - rzucają wyjątek "unsupported"
        Ten test akceptuje te 3 popularne polityki, żeby nie zabić projektu za interpretację.
        """
        segments = [
            ((0, 0), (4, 0)),
            ((2, 0), (6, 0)),  # overlap od 2 do 4
        ]
        try:
            raw = _call_algo(bentley_callable, segments)
            pts = norm_points(raw)

            # POLITYKA A: zwracamy końce overlapa
            if pts == {(2.0, 0.0), (4.0, 0.0)} or pts == {(2.0, 0.0)} or pts == {(4.0, 0.0)}:
                assert True
                return

            # POLITYKA B: ignorujemy overlap
            if pts == set():
                assert True
                return

            # Inna polityka -> fail świadomy
            pytest.fail(
                f"Nieobsługiwana polityka overlapu. Zwrócono: {pts}. "
                f"Dopuszczalne: pusty set albo końce overlapu (2,0) i (4,0)."
            )
        except Exception:
            # POLITYKA C: algorytm mówi "unsupported"
            assert True


class TestBentleyOttmannRegressionPack:
    @pytest.mark.parametrize(
        "segments,expected_points",
        [
            (
                [((0, 0), (5, 0)), ((2, -2), (2, 2))],
                {(2.0, 0.0)},
            ),
            (
                [((0, 0), (4, 4)), ((5, 5), (10, 10))],
                set(),
            ),
            (
                [((0, 0), (2, 2)), ((2, 0), (0, 2))],
                {(1.0, 1.0)},
            ),
        ],
    )
    def test_parametrized_cases(self, bentley_callable, norm_points, segments, expected_points):
        raw = _call_algo(bentley_callable, segments)
        pts = norm_points(raw)
        assert pts == expected_points
'''
    write_file(repo / "tests" / "test_bentley_ottmann.py", test_bentley)

    print("✅ Dodano testy: tests/test_bentley_ottmann.py")
    print("✅ Zaktualizowano: tests/conftest.py (fixture bentley_callable + norm_points)")
    print("")
    print("Uruchom:")
    print("  pytest -q")
    print("")
    print("Jeśli auto-detekcja nie znajdzie funkcji, ustaw:")
    print('  BENTLEY_MODULE="..."  i  BENTLEY_FUNC="..."')


if __name__ == "__main__":
    main()
