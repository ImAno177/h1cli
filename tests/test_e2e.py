"""End-to-end: real entry point and every command group, HTTP always faked."""
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HACKERONE_", "H1_"))}
    env["PYTHONPATH"] = str(ROOT / "src")
    return env


def test_entry_point_resolves_to_cli_main():
    # no tomllib on Python 3.10; the line is simple enough to read directly
    line = next(l for l in (ROOT / "pyproject.toml").read_text().splitlines() if l.startswith("h1cli ="))
    target = line.split("=", 1)[1].strip().strip('"')
    mod, func = target.split(":")
    assert target == "h1cli.cli:main"
    assert callable(getattr(import_module(mod), func))


def test_module_help_runs():
    r = subprocess.run([sys.executable, "-m", "h1cli", "--help"], env=_env(), capture_output=True, text=True)
    assert r.returncode == 0 and "intents" in r.stdout


def test_missing_creds_exit_2_without_network():
    r = subprocess.run([sys.executable, "-m", "h1cli", "balance"], env=_env(), capture_output=True, text=True)
    assert r.returncode == 2 and "HACKERONE_USERNAME" in r.stderr


@pytest.mark.parametrize("argv", [
    ["whoami"], ["reports", "list"], ["reports", "get", "1"], ["programs", "list"],
    ["programs", "get", "acme"], ["scopes", "acme"], ["weaknesses", "acme"],
    ["exclusions", "acme"], ["balance"], ["earnings"], ["payouts"], ["hacktivity"],
    ["intents", "list"], ["intents", "get", "1"], ["intents", "attachments", "list", "1"],
])
def test_every_read_command_runs(run, opener, argv):
    assert run(*argv) == 0
    assert all(m == "GET" for m in opener.methods)
