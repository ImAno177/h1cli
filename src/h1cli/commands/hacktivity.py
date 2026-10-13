"""hacktivity commands."""

from __future__ import annotations

import argparse

from ..client import H1Client
from ..output import _print_json, _program_handle, _trunc, _pages


def cmd_hacktivity(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(
        client,
        args,
        lambda p, s: client.hacktivity(query=args.query, sort=args.sort, page=p, size=s),
    )
    if args.json:
        _print_json(data)
        return 0
    for r in data.get("data") or []:
        a = r.get("attributes") or {}
        prog = _program_handle(r)
        print(
            f"{r.get('id')}\t{a.get('severity_rating') or '-'}\t{prog}\t{_trunc(a.get('title') or '(undisclosed)', 60)}"
        )
    return 0
