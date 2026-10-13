import json

import pytest

from h1cli.client import H1Client
from conftest import FakeOpener


def scope(i, ident, typ="URL", bounty=True, submit=True):
    return {"id": str(i), "type": "structured-scope", "attributes": {
        "asset_identifier": ident, "asset_type": typ,
        "eligible_for_bounty": bounty, "eligible_for_submission": submit}}


PAGES = {
    1: [scope(1, "a.example.com"), scope(2, "*.example.com", "WILDCARD"),
        scope(3, "com.example.app", "GOOGLE_PLAY_APP_ID", bounty=False)],
    2: [scope(4, "old.example.com", submit=False), scope(5, "a.example.com")],
}


def paged(req, q):
    page = int(q["page[number]"])
    return {"data": PAGES.get(page, []), "links": {"next": "x"} if page < 2 else {}}


@pytest.fixture(autouse=True)
def _paged(opener):
    opener.handler = paged


def test_all_structured_scopes_follows_pages():
    op = FakeOpener(paged)
    items = H1Client(username="u", token="t", opener=op).all_structured_scopes("acme", size=3)
    assert [s["id"] for s in items] == ["1", "2", "3", "4", "5"]
    assert len(op.urls) == 2
    assert "/hackers/programs/acme/structured_scopes" in op.urls[0]


def test_targets_dedup_and_drop_ineligible(run, opener, capsys):
    assert run(*["scopes", "acme", "--targets"]) == 0
    out = capsys.readouterr().out.split()
    assert out == ["a.example.com", "*.example.com", "com.example.app"]


def test_targets_bounty_and_type_filter(run, opener, capsys):
    assert run(*["scopes", "acme", "--targets", "--bounty-only", "--type", "wildcard"]) == 0
    assert capsys.readouterr().out.split() == ["*.example.com"]


def test_include_ineligible_json(run, opener, capsys):
    assert run(*["scopes", "acme", "--all", "--include-ineligible", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [s["id"] for s in data["data"]] == ["1", "2", "3", "4", "5"]


def test_plain_scopes_unchanged(run, opener, capsys):
    assert run(*["scopes", "acme"]) == 0
    out = capsys.readouterr().out
    assert "a.example.com" in out and len(opener.urls) == 1
