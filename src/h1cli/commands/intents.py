"""intents commands."""

from __future__ import annotations

import argparse
import sys

from ..client import H1Client
from ..output import _print_json, _trunc


def cmd_intents_list(client: H1Client, args: argparse.Namespace) -> int:
    data = client.list_report_intents()
    if args.json:
        _print_json(data)
        return 0
    for i in data.get("data") or []:
        a = i.get("attributes") or {}
        print(f"{i.get('id')}\t{a.get('state')}\t{_trunc(a.get('title') or '', 60)}")
    return 0


def cmd_intents_get(client: H1Client, args: argparse.Namespace) -> int:
    data = client.get_report_intent(args.id)
    _print_json(data)
    return 0


def cmd_intents_create(client: H1Client, args: argparse.Namespace) -> int:
    desc = args.description_file.read() if args.description_file else args.description
    data = client.create_report_intent(args.program, desc)
    _print_json(data)
    return 0


def cmd_intents_update(client: H1Client, args: argparse.Namespace) -> int:
    desc = args.description_file.read() if args.description_file else args.description
    data = client.update_report_intent(args.id, desc)
    _print_json(data)
    return 0


def cmd_intents_delete(client: H1Client, args: argparse.Namespace) -> int:
    if not args.confirm:
        print("Refusing to delete without --confirm.", file=sys.stderr)
        return 2
    data = client.delete_report_intent(args.id)
    if data is not None:
        _print_json(data)
    else:
        print("deleted")
    return 0


def cmd_intents_submit(client: H1Client, args: argparse.Namespace) -> int:
    if not args.confirm:
        print("Refusing to submit without --confirm.", file=sys.stderr)
        return 2
    data = client.submit_report_intent(args.id)
    _print_json(data)
    return 0


def cmd_intents_attachments(client: H1Client, args: argparse.Namespace) -> int:
    data = client.list_intent_attachments(args.id)
    _print_json(data)
    return 0


def cmd_intents_attachment_delete(client: H1Client, args: argparse.Namespace) -> int:
    if not args.confirm:
        print("Refusing to delete without --confirm.", file=sys.stderr)
        return 2
    data = client.delete_intent_attachment(args.id, args.attachment_id)
    if data is not None:
        _print_json(data)
    else:
        print("deleted")
    return 0
