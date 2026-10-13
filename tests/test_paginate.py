import pytest

from conftest import FakeOpener
from h1cli.client import H1Client


def make(pages):
    def handler(req, q):
        n = int(q["page[number]"])
        return {"data": pages.get(n, []), "links": {"next": "x"} if n + 1 in pages else {}}
    return handler


def rep(i, state, prog="acme"):
    return {"id": str(i), "attributes": {"id": i, "state": state, "title": f"r{i}"},
            "relationships": {"program": {"data": {"attributes": {"handle": prog}}}}}


def test_paginate_stops_without_next(client, opener):
    opener.handler = make({1: [1, 2], 2: [3]})
    assert client.paginate(lambda p, s: client.list_reports(page=p, size=s)) == [1, 2, 3]
    assert len(opener.requests) == 2


def test_paginate_respects_max_pages():
    endless = FakeOpener(lambda req, q: {"data": [{"id": q["page[number]"]}], "links": {"next": "x"}})
    c = H1Client(username="u", token="t", opener=endless)
    assert len(c.paginate(lambda p, s: c.list_reports(page=p, size=s), max_pages=3)) == 3
    assert len(endless.requests) == 3


def test_reports_list_all_filters_across_pages(run, opener, capsys):
    opener.handler = make({1: [rep(1, "resolved")], 2: [rep(2, "triaged"), rep(3, "new", "other")]})
    assert run("reports", "list", "--state", "open", "--program", "acme", "--all") == 0
    out = capsys.readouterr().out
    assert "r2" in out and "r1" not in out and "r3" not in out and "(1 shown)" in out


def test_reports_list_default_single_page(run, opener):
    opener.handler = make({1: [rep(1, "new")], 2: [rep(2, "new")]})
    assert run("reports", "list") == 0
    assert len(opener.requests) == 1


@pytest.mark.parametrize("argv", [["programs", "list"], ["weaknesses", "acme"], ["earnings"], ["payouts"], ["hacktivity"]])
def test_list_commands_accept_all(run, opener, argv):
    opener.handler = make({1: [{"id": "1", "attributes": {}}], 2: [{"id": "2", "attributes": {}}]})
    assert run(*argv, "--all") == 0
    assert len(opener.requests) == 2


def test_paginate_without_links_continues_on_capped_full_pages(client, opener):
    # live hacktivity: no links.next ever, size capped at 50 even when 100 is asked
    def handler(req, q):
        n = int(q["page[number]"])
        count = {1: 50, 2: 50, 3: 7}.get(n, 0)
        return {"data": [{"id": f"{n}-{i}"} for i in range(count)], "links": {}}
    opener.handler = handler
    items = client.paginate(lambda p, s: client.hacktivity(page=p, size=s), size=100)
    assert len(items) == 107 and len(opener.requests) == 3


def test_paginate_stops_on_repeated_page(client, opener):
    opener.handler = lambda req, q: {"data": [{"id": str(i)} for i in range(50)], "links": {}}
    assert len(client.paginate(lambda p, s: client.hacktivity(page=p, size=s))) == 50
    assert len(opener.requests) == 2


def test_paginate_small_page_without_next_stops(client, opener):
    opener.handler = lambda req, q: {"data": [{"id": "1"}], "links": {}}
    client.paginate(lambda p, s: client.list_reports(page=p, size=s))
    assert len(opener.requests) == 1


def test_hacktivity_undisclosed_title(run, opener, capsys):
    opener.handler = lambda req, q: {"data": [{"id": 9, "attributes": {"title": None}}]}
    assert run("hacktivity") == 0
    assert "(undisclosed)" in capsys.readouterr().out
