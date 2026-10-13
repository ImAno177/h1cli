import base64

import pytest

from h1cli.client import OPEN_STATES, H1Client, H1Error
from conftest import FakeOpener, http_error


def test_open_states():
    assert {"new", "triaged"} <= OPEN_STATES


def test_missing_creds(monkeypatch):
    for k in ("HACKERONE_USERNAME", "HACKERONE_API_TOKEN", "H1_USERNAME", "H1_API_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(H1Error):
        H1Client()


def test_list_reports_builds_path(client, opener):
    client.list_reports(page=2, size=10)
    assert opener.methods == ["GET"]
    url = opener.urls[0]
    assert "/hackers/me/reports?" in url
    assert "page%5Bnumber%5D=2" in url and "page%5Bsize%5D=10" in url


def test_get_program_path(client, opener):
    client.get_program("tron_dao")
    assert opener.urls[0].endswith("/hackers/programs/tron_dao")


def test_basic_auth_header_sent_preemptively(opener):
    c = H1Client(username="alice", token="s3cr3t", opener=opener)
    c.list_reports()
    c.post("/hackers/report_intents", {"x": 1})
    expected = "Basic " + base64.b64encode(b"alice:s3cr3t").decode()
    assert [r.get_header("Authorization") for r in opener.requests] == [expected, expected]


def test_handle_slash_is_encoded(client, opener):
    client.structured_scopes("a/../b")
    assert "/hackers/programs/a%2F..%2Fb/structured_scopes?" in opener.urls[0]


def test_intent_ids_encoded(client, opener):
    client.delete_intent_attachment("1/..", "2?x")
    assert opener.urls[0].endswith("/hackers/report_intents/1%2F../attachments/2%3Fx")


@pytest.mark.parametrize("code,msg", [(401, "Unauthorized"), (403, "Forbidden"), (429, "Rate limited"), (500, "HTTP 500")])
def test_http_errors(code, msg):
    c = H1Client(username="u", token="t", opener=FakeOpener(http_error(code, {"errors": ["x"]})))
    with pytest.raises(H1Error) as e:
        c.list_reports()
    assert msg in str(e.value) and e.value.status == code
    assert e.value.body == {"errors": ["x"]}
