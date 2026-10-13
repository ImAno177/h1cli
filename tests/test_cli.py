import pytest

from h1cli import cli
from conftest import http_error


@pytest.mark.parametrize("argv", [["reports", "get", "1/../5"], ["intents", "delete", "abc", "--confirm"]])
def test_cli_rejects_non_int_ids(argv):
    with pytest.raises(SystemExit) as e:
        cli.build_parser().parse_args(argv)
    assert e.value.code == 2


@pytest.mark.parametrize("argv", [
    ["reports", "create", "--program", "p", "--title", "t", "--impact", "i"],
    ["intents", "delete", "1"],
    ["intents", "submit", "1"],
])
def test_confirm_required_sends_nothing(run, opener, argv, capsys):
    assert run(*argv) == 2
    assert opener.requests == []
    assert "--confirm" in capsys.readouterr().err


def test_confirm_allows_delete(run, opener):
    opener.handler = lambda req, q: None
    assert run("intents", "delete", "7", "--confirm") == 0
    assert opener.methods == ["DELETE"] and opener.urls[0].endswith("/report_intents/7")


@pytest.mark.parametrize("code", [401, 429])
def test_cli_http_error_exit_1(run, opener, code, capsys):
    opener.handler = http_error(code)
    assert run("balance") == 1
    assert str(code) in capsys.readouterr().err
