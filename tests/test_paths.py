import json

import pytest

from h1cli import cli
from h1cli.client import H1Client


class _Resp:
    def read(self):
        return json.dumps({"data": {}}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    def __init__(self):
        self.urls = []

    def open(self, req, timeout=60):
        self.urls.append(req.full_url)
        return _Resp()


def test_handle_slash_is_encoded():
    op = Opener()
    H1Client(username="u", token="t", opener=op).structured_scopes("a/../b")
    assert "/hackers/programs/a%2F..%2Fb/structured_scopes?" in op.urls[0]


def test_intent_ids_encoded():
    op = Opener()
    H1Client(username="u", token="t", opener=op).delete_intent_attachment("1/..", "2?x")
    assert op.urls[0].endswith("/hackers/report_intents/1%2F../attachments/2%3Fx")


@pytest.mark.parametrize("argv", [
    ["reports", "get", "1/../5"],
    ["intents", "delete", "abc", "--confirm"],
])
def test_cli_rejects_non_int_ids(argv, capsys):
    with pytest.raises(SystemExit) as e:
        cli.build_parser().parse_args(argv)
    assert e.value.code == 2
