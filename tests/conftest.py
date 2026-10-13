"""Shared fakes: no test ever touches the network or needs a real token."""
import io
import json
import urllib.error
from urllib.parse import parse_qs, urlparse

import pytest

from h1cli import cli
from h1cli.client import H1Client


class FakeResponse:
    def __init__(self, payload=None):
        self._payload = payload

    def read(self):
        return b"" if self._payload is None else json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """Records requests; `handler(req, query)` returns a payload or raises."""

    def __init__(self, handler=None):
        self.requests = []
        self.handler = handler or (lambda req, q: {"data": []})

    def open(self, req, timeout=60):
        self.requests.append(req)
        q = {k: v[0] for k, v in parse_qs(urlparse(req.full_url).query).items()}
        return FakeResponse(self.handler(req, q))

    @property
    def urls(self):
        return [r.full_url for r in self.requests]

    @property
    def methods(self):
        return [r.get_method() for r in self.requests]


def http_error(code, body=None):
    def raise_(req, q):
        raise urllib.error.HTTPError(
            req.full_url, code, "err", {}, io.BytesIO(json.dumps(body or {}).encode())
        )
    return raise_


@pytest.fixture
def opener():
    return FakeOpener()


@pytest.fixture
def client(opener):
    return H1Client(username="u", token="t", opener=opener)


@pytest.fixture
def run(monkeypatch, opener):
    """Run the CLI with a fake client; returns the exit code."""
    monkeypatch.setattr(cli, "H1Client", lambda: H1Client(username="u", token="t", opener=opener))
    return lambda *argv: cli.main(list(argv))
