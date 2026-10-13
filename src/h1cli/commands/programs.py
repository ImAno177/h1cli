"""programs commands."""

from __future__ import annotations

import argparse

from ..client import H1Client
from ..output import _print_json, _pages


def cmd_programs_list(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(client, args, lambda p, s: client.list_programs(page=p, size=s))
    if args.json:
        _print_json(data)
        return 0
    print(f"{'HANDLE':<24} {'STATE':<16} NAME")
    for p in data.get("data") or []:
        a = p.get("attributes") or {}
        print(
            f"{str(a.get('handle') or '-'):<24} "
            f"{str(a.get('submission_state') or a.get('state') or '-'):<16} "
            f"{a.get('name') or ''}"
        )
    return 0


def cmd_program_get(client: H1Client, args: argparse.Namespace) -> int:
    data = client.get_program(args.handle)
    if args.json or args.policy:
        if args.policy and not args.json:
            print(((data.get("data") or {}).get("attributes") or {}).get("policy") or "")
        else:
            _print_json(data)
        return 0
    a = (data.get("data") or {}).get("attributes") or {}
    for k in (
        "handle",
        "name",
        "submission_state",
        "state",
        "offers_bounties",
        "currency",
        "bounty_earned_for_user",
        "number_of_reports_for_user",
    ):
        print(f"{k}: {a.get(k)}")
    return 0


def _filter_scopes(items: list, args: argparse.Namespace) -> list:
    types = {t.strip().upper() for t in (args.type or "").split(",") if t.strip()}
    out = []
    for s in items:
        a = s.get("attributes") or {}
        if args.bounty_only and not a.get("eligible_for_bounty"):
            continue
        if not args.include_ineligible and a.get("eligible_for_submission") is False:
            continue
        if types and str(a.get("asset_type") or "").upper() not in types:
            continue
        out.append(s)
    return out


def cmd_scopes(client: H1Client, args: argparse.Namespace) -> int:
    filtering = args.all or args.targets or args.bounty_only or args.type
    if filtering:
        items = client.all_structured_scopes(args.handle) if (args.all or args.targets) else list(
            (client.structured_scopes(args.handle, page=args.page, size=args.size) or {}).get("data") or []
        )
        items = _filter_scopes(items, args)
        if args.targets:
            seen = set()
            for s in items:
                ident = ((s.get("attributes") or {}).get("asset_identifier") or "").strip()
                if ident and ident not in seen:
                    seen.add(ident)
                    print(ident)
            return 0
        data = {"data": items}
    else:
        data = client.structured_scopes(args.handle, page=args.page, size=args.size)
    if args.json:
        _print_json(data)
        return 0
    print(f"{'ID':<10} {'TYPE':<16} {'BOUNTY':<8} ASSET")
    for s in data.get("data") or []:
        a = s.get("attributes") or {}
        print(
            f"{str(s.get('id')):<10} {str(a.get('asset_type') or '-'):<16} "
            f"{str(a.get('eligible_for_bounty')):<8} {a.get('asset_identifier')}"
        )
    return 0


def cmd_weaknesses(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(
        client, args, lambda p, s: client.weaknesses(args.handle, page=p, size=s)
    )
    if args.json:
        _print_json(data)
        return 0
    for w in data.get("data") or []:
        a = w.get("attributes") or {}
        print(f"{w.get('id')}\t{a.get('external_id') or ''}\t{a.get('name')}")
    return 0


def cmd_exclusions(client: H1Client, args: argparse.Namespace) -> int:
    data = client.scope_exclusions(args.handle)
    if args.json:
        _print_json(data)
        return 0
    for x in data.get("data") or []:
        a = x.get("attributes") or {}
        print(f"- {a.get('category')}: {a.get('details')}")
    return 0
