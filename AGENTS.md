# AGENTS.md

Guide for coding agents working on h1cli.

## Purpose

`h1cli` is a command-line client for the HackerOne **Hacker API** (`https://api.hackerone.com/v1`), authenticated with a personal API token over HTTP Basic. Python 3.10+, standard library only (no runtime dependencies).

## Layout

```
src/h1cli/
  __main__.py      # `python -m h1cli`
  cli.py           # build_parser() + main(); entry point h1cli.cli:main
  client.py        # H1Client: HTTP, auth, errors, paginate(), one method per endpoint
  output.py        # print/format helpers and _pages() (one page vs --all)
  commands/
    reports.py     # whoami, reports list/get/create
    programs.py    # programs list/get, scopes, weaknesses, exclusions
    payments.py    # balance, earnings, payouts
    hacktivity.py  # hacktivity
    intents.py     # intents ... and intents attachments list/delete
tests/
  conftest.py      # FakeOpener, FakeResponse, http_error(); fixtures opener, client, run
  test_*.py
```

Where things go:
- New API endpoint → a method on `H1Client` in `client.py`.
- New command handler → `cmd_<name>(client, args) -> int` in the matching `commands/*.py`.
- Argument parsing and wiring → `build_parser()` in `cli.py`.
- Shared formatting → `output.py`.

## Run and test

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

Tests never touch the network and need no token. HTTP is faked by passing a `FakeOpener` as `H1Client(opener=...)`. The `run` fixture runs `cli.main([...])` with a faked client:

```python
def test_balance(run, opener, capsys):
    opener.handler = lambda req, query: {"data": {"balance": 5}}
    assert run("balance") == 0
    assert opener.urls[0].endswith("/hackers/payments/balance")
```

Raise HTTP errors with `opener.handler = http_error(429)`.

## Conventions

- **Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), one small change per commit. Run `pytest -q` and see it pass before pushing straight to `main`.
- **Destructive or submitting commands** (create, submit, delete) refuse to act without `--confirm`. They return exit code 2 and make no request. Add a test that proves no request was sent.
- **Path parameters:** wrap every value placed in a URL path with `_seg()` in `client.py` (`quote(x, safe="")`). Numeric IDs are declared as `type=int` in argparse.
- **Pagination:** list endpoints take `page`/`size`. Fetch everything with `client.paginate(lambda p, s: client.method(..., page=p, size=s))`. It follows `links.next` and stops at `MAX_PAGES`. In commands, call `_pages(client, args, fetch_page)` so that `--all` works.
- **Shared flags:** use the parent parsers in `build_parser()`. `parents=[json_p]` adds `--json`, and `parents=paged` adds `--json --page --size --all`.
- **Exit codes:** 0 ok, 1 API error (`H1Error`), 2 usage error, missing credentials or missing `--confirm`.
- **Secrets:** credentials come only from `HACKERONE_USERNAME`/`HACKERONE_API_TOKEN` (or `H1_USERNAME`/`H1_API_TOKEN`). Never print, log, hard-code or commit them. Tests use dummy values such as `"u"`/`"t"`.

## Adding a command

1. Add the endpoint method to `H1Client` (use `_seg()` for path values and `page`/`size` params if it lists items).
2. Write `cmd_<name>` in the right `commands/*.py`. Support `--json` via `_print_json` from `output.py`, and use `_pages` for lists.
3. Import it in `cli.py` and register it in `build_parser()` with the right parents. Destructive commands also need `--confirm`.
4. Add tests with the `run`/`opener` fixtures, covering the URL and method plus output (and the `--confirm` refusal if relevant).
5. Update the command table in `README.md`.
6. Run `pytest -q`, commit, and push.
