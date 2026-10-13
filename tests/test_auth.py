import base64
import json

from h1cli.client import H1Client


class _Resp:
    def read(self):
        return json.dumps({"data": []}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_basic_auth_header_sent_preemptively():
    seen = []

    class Opener:
        def open(self, req, timeout=60):
            seen.append(req.get_header("Authorization"))
            return _Resp()

    c = H1Client(username="alice", token="s3cr3t", opener=Opener())
    c.list_reports()
    c.post("/hackers/report_intents", {"x": 1})
    expected = "Basic " + base64.b64encode(b"alice:s3cr3t").decode()
    assert seen == [expected, expected]
