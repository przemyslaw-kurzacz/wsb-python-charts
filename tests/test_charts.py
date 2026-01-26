"""Tests for additional visualization endpoints (matplotlib + seaborn)."""

from __future__ import annotations

from io import BytesIO

import pytest


def _upload_csv(authenticated_client, content: bytes, filename: str = "data.csv"):
    return authenticated_client.post(
        "/index",
        data={"file": (BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


@pytest.fixture()
def csv_bytes():
    def _mk(s: str) -> bytes:
        return s.encode("utf-8")
    return _mk


class TestAPICharts:
    def test_line_missing_box_hist_return_png(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("date,a,b\n2024-01-01,1,10\n2024-01-02,2,11\n"))
        assert upload_resp.status_code == 200

        for url in [
            "/api/charts/line?x=date&y=a",
            "/api/charts/missing",
            "/api/charts/boxplot",
            "/api/charts/hist?col=a",
        ]:
            resp = authenticated_client.get(url)
            assert resp.status_code == 200
            assert resp.headers.get("Content-Type", "").startswith("image/png")
            assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_missing_values_chart_works_without_numeric_columns(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("name\nala\nola\n"))
        assert upload_resp.status_code == 200

        resp = authenticated_client.get("/api/charts/missing")
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("image/png")

    def test_line_box_hist_fail_without_numeric_columns(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("name\nala\nola\n"))
        assert upload_resp.status_code == 200

        for url in ["/api/charts/line", "/api/charts/boxplot", "/api/charts/hist"]:
            resp = authenticated_client.get(url)
            assert resp.status_code == 400
            data = resp.get_json()
            assert "error" in data
