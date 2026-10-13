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


def test_attachment_delete_requires_confirm(run, opener):
    assert run("intents", "attachments", "delete", "7", "9") == 2
    assert opener.requests == []


def test_attachment_delete_with_confirm(run, opener, capsys):
    opener.handler = lambda req, q: None
    assert run("intents", "attachments", "delete", "7", "9", "--confirm") == 0
    assert opener.methods == ["DELETE"]
    assert opener.urls[0].endswith("/hackers/report_intents/7/attachments/9")
    assert "deleted" in capsys.readouterr().out


def test_attachment_list(run, opener):
    assert run("intents", "attachments", "list", "7") == 0
    assert opener.urls[0].endswith("/hackers/report_intents/7/attachments")


@pytest.mark.parametrize("argv", [["reports", "list"], ["scopes", "x"], ["earnings"], ["hacktivity"]])
def test_shared_paging_flags(argv):
    a = cli.build_parser().parse_args(argv + ["--json", "--page", "3", "--size", "5", "--all"])
    assert (a.json, a.page, a.size, a.all) == (True, 3, 5, True)


def test_intents_get_prints_json(run, opener, capsys):
    opener.handler = lambda req, q: {"data": {"id": "4"}}
    assert run("intents", "get", "4") == 0
    assert '"id": "4"' in capsys.readouterr().out
