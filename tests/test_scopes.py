import json
from urllib.parse import parse_qs, urlparse

import pytest

from h1cli import cli
from h1cli.client import H1Client


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def scope(i, ident, typ="URL", bounty=True, submit=True):
    return {"id": str(i), "type": "structured-scope", "attributes": {
        "asset_identifier": ident, "asset_type": typ,
        "eligible_for_bounty": bounty, "eligible_for_submission": submit}}


PAGES = {
    1: [scope(1, "a.example.com"), scope(2, "*.example.com", "WILDCARD"),
        scope(3, "com.example.app", "GOOGLE_PLAY_APP_ID", bounty=False)],
    2: [scope(4, "old.example.com", submit=False), scope(5, "a.example.com")],
}


class PagedOpener:
    def __init__(self):
        self.urls = []

    def open(self, req, timeout=60):
        self.urls.append(req.full_url)
        q = parse_qs(urlparse(req.full_url).query)
        page = int(q["page[number]"][0])
        links = {"next": "x"} if page < 2 else {}
        return FakeResponse({"data": PAGES.get(page, []), "links": links})


@pytest.fixture
def opener(monkeypatch):
    op = PagedOpener()
    monkeypatch.setattr(cli, "H1Client", lambda: H1Client(username="u", token="t", opener=op))
    return op


def test_all_structured_scopes_follows_pages():
    op = PagedOpener()
    items = H1Client(username="u", token="t", opener=op).all_structured_scopes("acme", size=3)
    assert [s["id"] for s in items] == ["1", "2", "3", "4", "5"]
    assert len(op.urls) == 2
    assert "/hackers/programs/acme/structured_scopes" in op.urls[0]


def test_targets_dedup_and_drop_ineligible(opener, capsys):
    assert cli.main(["scopes", "acme", "--targets"]) == 0
    out = capsys.readouterr().out.split()
    assert out == ["a.example.com", "*.example.com", "com.example.app"]


def test_targets_bounty_and_type_filter(opener, capsys):
    assert cli.main(["scopes", "acme", "--targets", "--bounty-only", "--type", "wildcard"]) == 0
    assert capsys.readouterr().out.split() == ["*.example.com"]


def test_include_ineligible_json(opener, capsys):
    assert cli.main(["scopes", "acme", "--all", "--include-ineligible", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [s["id"] for s in data["data"]] == ["1", "2", "3", "4", "5"]


def test_plain_scopes_unchanged(opener, capsys):
    assert cli.main(["scopes", "acme"]) == 0
    out = capsys.readouterr().out
    assert "a.example.com" in out and len(opener.urls) == 1
