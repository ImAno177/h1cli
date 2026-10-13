import io
import json
import unittest
from unittest import mock

from h1cli.client import H1Client, H1Error, OPEN_STATES


class FakeResponse:
    def __init__(self, payload, code=200):
        self._payload = payload
        self.code = code

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClientTests(unittest.TestCase):
    def test_open_states(self):
        self.assertIn("new", OPEN_STATES)
        self.assertIn("triaged", OPEN_STATES)

    def test_missing_creds(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(H1Error):
                H1Client(username=None, token=None)

    def test_list_reports_builds_path(self):
        calls = []

        class Opener:
            def open(self, req, timeout=60):
                calls.append((req.get_method(), req.full_url))
                return FakeResponse({"data": [], "links": {}})

        c = H1Client(username="u", token="t", opener=Opener())
        c.list_reports(page=2, size=10)
        method, url = calls[0]
        self.assertEqual(method, "GET")
        self.assertIn("/hackers/me/reports?", url)
        self.assertIn("page%5Bnumber%5D=2", url)
        self.assertIn("page%5Bsize%5D=10", url)

    def test_get_program_quotes_handle(self):
        calls = []

        class Opener:
            def open(self, req, timeout=60):
                calls.append(req.full_url)
                return FakeResponse({"data": {}})

        c = H1Client(username="u", token="t", opener=Opener())
        c.get_program("tron_dao")
        self.assertTrue(calls[0].endswith("/hackers/programs/tron_dao"))


if __name__ == "__main__":
    unittest.main()
