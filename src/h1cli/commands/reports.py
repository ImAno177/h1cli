"""reports commands."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..client import OPEN_STATES, H1Client, H1Error
from ..output import _print_json, _program_handle, _trunc, _pages


def cmd_whoami(client: H1Client, _args: argparse.Namespace) -> int:
    print(f"username: {client.username}")
    try:
        client.list_reports(page=1, size=1)
        print("api: ok")
        return 0
    except H1Error as e:
        print(f"api: fail ({e})", file=sys.stderr)
        return 1


def cmd_reports_list(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(client, args, lambda p, s: client.list_reports(page=p, size=s))
    items = list(data.get("data") or [])
    if args.state == "open":
        items = [r for r in items if (r.get("attributes") or {}).get("state") in OPEN_STATES]
    elif args.state:
        items = [
            r for r in items if (r.get("attributes") or {}).get("state") == args.state
        ]
    if args.program:
        items = [r for r in items if _program_handle(r) == args.program]
    if args.json:
        _print_json({"data": items, "links": data.get("links")})
        return 0
    print(f"{'ID':<10} {'STATE':<22} {'PROGRAM':<16} TITLE")
    for r in items:
        a = r.get("attributes") or {}
        rid = a.get("id") or r.get("id")
        print(
            f"{str(rid):<10} {str(a.get('state') or '-'):<22} "
            f"{_program_handle(r):<16} {_trunc(a.get('title') or '')}"
        )
    print(f"({len(items)} shown)")
    return 0


def cmd_reports_get(client: H1Client, args: argparse.Namespace) -> int:
    data = client.get_report(args.id)
    if args.json:
        _print_json(data)
        return 0
    report = data.get("data") or {}
    a = report.get("attributes") or {}
    print(f"id:       {a.get('id') or report.get('id')}")
    print(f"state:    {a.get('state')}")
    print(f"program:  {_program_handle(report)}")
    print(f"title:    {a.get('title')}")
    print(f"created:  {a.get('created_at')}")
    print(f"triaged:  {a.get('triaged_at')}")
    print(f"url:      https://hackerone.com/reports/{a.get('id') or report.get('id')}")
    if args.body:
        print("\n--- vulnerability_information ---\n")
        print(a.get("vulnerability_information") or "")
    return 0


def cmd_reports_create(client: H1Client, args: argparse.Namespace) -> int:
    if not args.confirm:
        print("Refusing to submit without --confirm.", file=sys.stderr)
        return 2
    attrs: dict[str, Any] = {
        "team_handle": args.program,
        "title": args.title,
        "vulnerability_information": args.body_file.read()
        if args.body_file
        else args.vulnerability_information,
        "impact": args.impact,
    }
    if args.severity:
        attrs["severity_rating"] = args.severity
    if args.weakness_id:
        attrs["weakness_id"] = args.weakness_id
    if args.scope_id:
        attrs["structured_scope_id"] = args.scope_id
    data = client.create_report(attrs)
    if args.json:
        _print_json(data)
    else:
        rid = (data.get("data") or {}).get("id")
        print(f"created report {rid}: https://hackerone.com/reports/{rid}")
    return 0
