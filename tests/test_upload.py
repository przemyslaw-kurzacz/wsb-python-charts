"""CSV upload tests grouped into a class."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest


class TestUploadCSV:
    def _user_upload_dir(self, app, username: str) -> Path:
        return Path(app.config["UPLOAD_FOLDER"]) / username

    def _post_csv(self, authenticated_client, csv_content: bytes, filename: str, follow_redirects: bool = True):
        return authenticated_client.post(
            "/index",
            data={"file": (BytesIO(csv_content), filename)},
            content_type="multipart/form-data",
            follow_redirects=follow_redirects,
        )

    def test_upload_form_visible_when_logged_in(self, authenticated_client):
        resp = authenticated_client.get("/index")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Prześlij plik" in html

    def test_upload_requires_authentication(self, client):
        resp = client.get("/index", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers.get("Location", "")

    @pytest.mark.parametrize(
        "csv_text,filename",
        [
            ("col1,col2\n1,2\n", "data.csv"),
            ("a;b\n1;2\n", "semicolon.csv"),
            ("", "empty.csv"),
        ],
    )
    def test_csv_upload_saves_file(self, authenticated_client, app, test_user, csv_bytes, csv_text, filename):
        resp = self._post_csv(authenticated_client, csv_bytes(csv_text), filename)
        assert resp.status_code == 200

        target = self._user_upload_dir(app, test_user["username"]) / filename
        assert target.exists()

    def test_upload_non_csv_extension_rejected(self, authenticated_client, csv_bytes):
        resp = authenticated_client.post(
            "/index",
            data={"file": (BytesIO(csv_bytes("x")), "not_csv.txt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "CSV" in html

    def test_upload_without_file_shows_validation_error(self, authenticated_client):
        resp = authenticated_client.post(
            "/index",
            data={},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "wybrać plik" in html.lower()

    def test_new_upload_replaces_old_file(self, authenticated_client, app, test_user, csv_bytes):
        first = self._post_csv(authenticated_client, csv_bytes("a,b\n1,2\n"), "first.csv", follow_redirects=False)
        assert first.status_code in (302, 303)

        second = self._post_csv(authenticated_client, csv_bytes("a,b\n3,4\n"), "second.csv", follow_redirects=True)
        assert second.status_code == 200

        folder = self._user_upload_dir(app, test_user["username"])
        files = sorted([p.name for p in folder.glob("*.csv")])
        assert files == ["second.csv"]

    def test_large_file_rejected_with_413(self, authenticated_client, app, test_user):
        big = b"x" * (300 * 1024)  # 300KB > MAX_CONTENT_LENGTH=256KB

        resp = authenticated_client.post(
            "/index",
            data={"file": (BytesIO(big), "big.csv")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code == 413

        target = self._user_upload_dir(app, test_user["username"]) / "big.csv"
        assert not target.exists()
