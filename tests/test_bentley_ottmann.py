"""Unit tests for Bentley–Ottmann algorithm (sweep line intersections).

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
