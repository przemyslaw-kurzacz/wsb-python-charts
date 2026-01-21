"""Core data processing + API tests grouped into classes."""

from __future__ import annotations

from io import BytesIO

import pytest

from app.main.processing import CSVValidationError, compute_statistics, parse_and_validate_csv


def _upload_csv(authenticated_client, content: bytes, filename: str = "data.csv"):
    return authenticated_client.post(
        "/index",
        data={"file": (BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


class TestProcessingCore:
    def test_parse_valid_comma_csv(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

        df = parse_and_validate_csv(str(p))
        assert df.shape == (2, 2)
        assert list(df.columns) == ["a", "b"]

    def test_parse_valid_semicolon_csv(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("a;b\n1;2\n", encoding="utf-8")

        df = parse_and_validate_csv(str(p))
        assert df.shape == (1, 2)

    @pytest.mark.parametrize(
        "content,expected_error",
        [
            ("", "empty"),
            ("a|b\n1|2\n", "delimiter"),
        ],
    )
    def test_parse_invalid_csv_raises(self, tmp_path, content, expected_error):
        p = tmp_path / "bad.csv"
        p.write_text(content, encoding="utf-8")

        with pytest.raises(CSVValidationError) as exc:
            parse_and_validate_csv(str(p))

        assert expected_error.lower() in str(exc.value).lower()

    def test_compute_statistics_basic(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

        df = parse_and_validate_csv(str(p))
        stats = compute_statistics(df)

        assert stats["rows"] == 2
        assert stats["cols"] == 2
        assert stats["columns"] == ["a", "b"]
        assert "a" in stats["numeric_columns"]
        assert stats["numeric_summary"]["a"]["mean"] == pytest.approx(2.0)

    def test_compute_statistics_with_non_numeric_values(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("value\n1\nx\n3\n", encoding="utf-8")

        df = parse_and_validate_csv(str(p))
        stats = compute_statistics(df)

        assert stats["rows"] == 3
        assert stats["cols"] == 1
        assert stats["numeric_columns"] == ["value"]
        assert stats["numeric_summary"]["value"]["non_numeric_as_nan"] == 1
        assert stats["numeric_summary"]["value"]["mean"] == pytest.approx(2.0)


class TestAPIStats:
    def test_api_stats_requires_login(self, client):
        resp = client.get("/api/stats", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers.get("Location", "")

    def test_api_stats_without_file_returns_400(self, authenticated_client):
        resp = authenticated_client.get("/api/stats")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_api_stats_returns_expected_values(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("a,b\n1,2\n3,4\n"))
        assert upload_resp.status_code == 200

        resp = authenticated_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["rows"] == 2
        assert data["cols"] == 2
        assert "a" in data["numeric_columns"]
        assert data["numeric_summary"]["a"]["mean"] == pytest.approx(2.0)


class TestAPIPlot:
    def test_api_plot_returns_png(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("a,b\n1,2\n3,4\n"))
        assert upload_resp.status_code == 200

        resp = authenticated_client.get("/api/plot")
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("image/png")
        assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_api_plot_without_numeric_columns_returns_400(self, authenticated_client, csv_bytes):
        upload_resp = _upload_csv(authenticated_client, csv_bytes("name\nala\nola\n"))
        assert upload_resp.status_code == 200

        resp = authenticated_client.get("/api/plot")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
