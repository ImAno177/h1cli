"""payments commands."""

from __future__ import annotations

import argparse

from ..client import H1Client
from ..output import _print_json, _pages


def cmd_balance(client: H1Client, args: argparse.Namespace) -> int:
    data = client.balance()
    if args.json:
        _print_json(data)
    else:
        print((data.get("data") or {}).get("balance"))
    return 0


def cmd_earnings(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(client, args, lambda p, s: client.earnings(page=p, size=s))
    if args.json:
        _print_json(data)
        return 0
    for e in data.get("data") or []:
        a = e.get("attributes") or {}
        print(f"{e.get('id')}\t{e.get('type')}\t{a.get('amount')}\t{a.get('created_at')}")
    return 0


def cmd_payouts(client: H1Client, args: argparse.Namespace) -> int:
    data = _pages(client, args, lambda p, s: client.payouts(page=p, size=s))
    if args.json:
        _print_json(data)
        return 0
    for p in data.get("data") or []:
        if isinstance(p, dict) and "attributes" in p:
            a = p["attributes"]
            print(
                f"{a.get('amount')}\t{a.get('status')}\t{a.get('payout_provider')}\t{a.get('paid_out_at')}"
            )
        else:
            print(
                f"{p.get('amount')}\t{p.get('status')}\t{p.get('payout_provider')}\t{p.get('paid_out_at')}"
            )
    return 0
