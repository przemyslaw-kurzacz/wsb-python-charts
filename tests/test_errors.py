"""Error pages tests grouped into a class."""

from __future__ import annotations


class TestErrors:
    def test_unknown_route_returns_custom_404(self, client):
        resp = client.get("/this-page-does-not-exist")
        assert resp.status_code == 404
        html = resp.get_data(as_text=True)
        assert "404" in html
