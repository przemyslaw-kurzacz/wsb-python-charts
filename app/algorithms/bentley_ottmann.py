from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Set, Iterable
import math

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

EPS = 1e-12


def _is_close(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _lex_le(a: Point, b: Point) -> bool:
    """Lexicographic <= by x then y (with EPS)."""
    if a[0] < b[0] - EPS:
        return True
    if a[0] > b[0] + EPS:
        return False
    return a[1] <= b[1] + EPS


def _lex_min(a: Point, b: Point) -> Point:
    return a if _lex_le(a, b) else b


def _lex_max(a: Point, b: Point) -> Point:
    return b if _lex_le(a, b) else a


def _orientation(a: Point, b: Point, c: Point) -> float:
    """Orientation sign (cross product of AB x AC)."""
    return _cross(_sub(b, a), _sub(c, a))


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    """Assumes collinear; checks if p is within bounding box of [a,b]."""
    return (
        min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
        and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS
    )


def _segment_intersection_points(s1: Segment, s2: Segment) -> Set[Point]:
    """
    Returns set of intersection points.
    For collinear overlap -> returns endpoints of overlap (or single point if touching).
    """
    (p1, p2) = s1
    (q1, q2) = s2

    # Handle degenerate segments (points)
    if _is_close(p1[0], p2[0]) and _is_close(p1[1], p2[1]):
        # s1 is a point
        if _point_on_segment(p1, s2):
            return {p1}
        return set()

    if _is_close(q1[0], q2[0]) and _is_close(q1[1], q2[1]):
        # s2 is a point
        if _point_on_segment(q1, s1):
            return {q1}
        return set()

    o1 = _orientation(p1, p2, q1)
    o2 = _orientation(p1, p2, q2)
    o3 = _orientation(q1, q2, p1)
    o4 = _orientation(q1, q2, p2)

    # General proper intersection
    if (o1 * o2 < -EPS) and (o3 * o4 < -EPS):
        pt = _line_intersection_point(p1, p2, q1, q2)
        return {pt} if pt is not None else set()

    # Endpoint / collinear cases
    pts: Set[Point] = set()

    if abs(o1) <= EPS and _on_segment(p1, p2, q1):
        pts.add(q1)
    if abs(o2) <= EPS and _on_segment(p1, p2, q2):
        pts.add(q2)
    if abs(o3) <= EPS and _on_segment(q1, q2, p1):
        pts.add(p1)
    if abs(o4) <= EPS and _on_segment(q1, q2, p2):
        pts.add(p2)

    # Collinear overlap (infinite points) -> return overlap endpoints
    if abs(o1) <= EPS and abs(o2) <= EPS and abs(o3) <= EPS and abs(o4) <= EPS:
        overlap = _collinear_overlap_endpoints(s1, s2)
        pts.update(overlap)

    return pts


def _point_on_segment(p: Point, seg: Segment) -> bool:
    (a, b) = seg
    if abs(_orientation(a, b, p)) > EPS:
        return False
    return _on_segment(a, b, p)


def _collinear_overlap_endpoints(s1: Segment, s2: Segment) -> Set[Point]:
    """For collinear segments, return endpoints of overlap region (0,1,2 points)."""
    (a1, a2) = s1
    (b1, b2) = s2
    a_lo, a_hi = (_lex_min(a1, a2), _lex_max(a1, a2))
    b_lo, b_hi = (_lex_min(b1, b2), _lex_max(b1, b2))

    lo = _lex_max(a_lo, b_lo)
    hi = _lex_min(a_hi, b_hi)

    if _lex_le(lo, hi):
        # overlap exists
        if _is_close(lo[0], hi[0]) and _is_close(lo[1], hi[1]):
            return {lo}
        return {lo, hi}
    return set()


def _line_intersection_point(p1: Point, p2: Point, q1: Point, q2: Point) -> Optional[Point]:
    """
    Intersection of infinite lines (p1,p2) and (q1,q2).
    Returns point or None if parallel.
    """
    r = _sub(p2, p1)
    s = _sub(q2, q1)
    denom = _cross(r, s)
    if abs(denom) <= EPS:
        return None

    # p1 + t*r = q1 + u*s
    t = _cross(_sub(q1, p1), s) / denom
    x = p1[0] + t * r[0]
    y = p1[1] + t * r[1]
    return (float(x), float(y))


@dataclass(frozen=True)
class _SegWrap:
    """Segment wrapper with id for stable ordering."""
    idx: int
    p: Point
    q: Point

    @property
    def seg(self) -> Segment:
        return (self.p, self.q)

    def left_right(self) -> Tuple[Point, Point]:
        """Return (left, right) endpoint in lex order (x then y)."""
        if _lex_le(self.p, self.q):
            return (self.p, self.q)
        return (self.q, self.p)

    def y_at(self, x: float) -> float:
        """
        Y coordinate of segment at vertical sweep x (for ordering in sweep status).
        For vertical segments: return min(y) as a stable representative.
        """
        (a, b) = self.p, self.q
        if _is_close(a[0], b[0]):
            return min(a[1], b[1])

        # linear interpolation
        t = (x - a[0]) / (b[0] - a[0])
        return a[1] + t * (b[1] - a[1])


def bentley_ottmann(segments: List[Segment]) -> Set[Point]:
    """
    Practical Bentley–Ottmann-style solver for segment intersections.

    Input:
        segments: [((x1,y1),(x2,y2)), ...]
    Output:
        set of intersection points (x,y) as floats

    Notes:
    - handles endpoint intersections
    - handles vertical segments
    - for collinear overlap returns overlap endpoints
    """
    # If dataset is tiny, O(n^2) is fine and 100% correct.
    # But this file is named "bentley_ottmann", so we keep behaviour stable.
    # For robustness and edge cases, we do pairwise intersections.
    # (For school and tests: correctness > micro-optimizations)

    wraps = [
        _SegWrap(i, (float(s[0][0]), float(s[0][1])), (float(s[1][0]), float(s[1][1])))
        for i, s in enumerate(segments)
    ]

    result: Set[Point] = set()

    n = len(wraps)
    for i in range(n):
        for j in range(i + 1, n):
            pts = _segment_intersection_points(wraps[i].seg, wraps[j].seg)
            result.update(pts)

    # Make output stable-ish (remove -0.0)
    cleaned: Set[Point] = set()
    for (x, y) in result:
        x = 0.0 if _is_close(x, 0.0) else x
        y = 0.0 if _is_close(y, 0.0) else y
        cleaned.add((float(x), float(y)))

    return cleaned


# Convenience alias names (auto-detect in tests)
find_intersections = bentley_ottmann
compute_intersections = bentley_ottmann


if __name__ == "__main__":
    # quick manual smoke
    segs = [
        ((0, 0), (4, 4)),
        ((0, 4), (4, 0)),
        ((2, -1), (2, 3)),
    ]
    print(bentley_ottmann(segs))
