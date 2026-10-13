"""argparse CLI for h1cli."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import __version__
from .client import H1Client, H1Error
from .commands.reports import cmd_whoami, cmd_reports_list, cmd_reports_get, cmd_reports_create
from .commands.programs import (
    cmd_programs_list,
    cmd_program_get,
    cmd_scopes,
    cmd_weaknesses,
    cmd_exclusions,
)
from .commands.payments import cmd_balance, cmd_earnings, cmd_payouts
from .commands.hacktivity import cmd_hacktivity
from .commands.intents import (
    cmd_intents_list,
    cmd_intents_get,
    cmd_intents_create,
    cmd_intents_update,
    cmd_intents_delete,
    cmd_intents_submit,
    cmd_intents_attachments,
    cmd_intents_attachment_delete,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="h1cli",
        description="CLI for the HackerOne Hacker API (personal token, HTTP Basic).",
    )
    json_p = argparse.ArgumentParser(add_help=False)
    json_p.add_argument("--json", action="store_true", help="Print raw JSON")
    page_p = argparse.ArgumentParser(add_help=False)
    page_p.add_argument("--page", type=int, default=1)
    page_p.add_argument("--size", type=int, default=25)
    page_p.add_argument("--all", action="store_true", help="Fetch every page")
    paged = [json_p, page_p]

    p.add_argument("--version", action="version", version=f"h1cli {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    w = sub.add_parser("whoami", help="Show username and smoke-test API auth")
    w.set_defaults(func=cmd_whoami)

    # reports
    reports = sub.add_parser("reports", help="Your vulnerability reports")
    rsub = reports.add_subparsers(dest="reports_cmd", required=True)
    rl = rsub.add_parser("list", help="List my reports", parents=paged)
    rl.add_argument("--state", help="Filter state, or 'open' for active states")
    rl.add_argument("--program", help="Filter by program handle")
    rl.set_defaults(func=cmd_reports_list)
    rg = rsub.add_parser("get", help="Get one report", parents=[json_p])
    rg.add_argument("id", type=int)
    rg.add_argument("--body", action="store_true", help="Print vulnerability_information")
    rg.set_defaults(func=cmd_reports_get)
    rc = rsub.add_parser("create", help="Submit a report (requires --confirm)", parents=[json_p])
    rc.add_argument("--program", required=True, help="team_handle")
    rc.add_argument("--title", required=True)
    rc.add_argument("--impact", required=True)
    rc.add_argument("--vulnerability-information", default="")
    rc.add_argument("--body-file", type=argparse.FileType("r"), dest="body_file")
    rc.add_argument("--severity", choices=["none", "low", "medium", "high", "critical"])
    rc.add_argument("--weakness-id", type=int)
    rc.add_argument("--scope-id", type=int)
    rc.add_argument("--confirm", action="store_true")
    rc.set_defaults(func=cmd_reports_create)

    programs = sub.add_parser("programs", help="Programs visible to you")
    psub = programs.add_subparsers(dest="programs_cmd", required=True)
    pl = psub.add_parser("list", parents=paged)
    pl.set_defaults(func=cmd_programs_list)
    pg = psub.add_parser("get", parents=[json_p])
    pg.add_argument("handle")
    pg.add_argument("--policy", action="store_true", help="Print policy markdown only")
    pg.set_defaults(func=cmd_program_get)

    sc = sub.add_parser("scopes", help="Structured scopes for a program", parents=paged)
    sc.add_argument("handle")
    sc.add_argument("--bounty-only", action="store_true", help="Only bounty-eligible assets")
    sc.add_argument("--type", help="Comma-separated asset types, e.g. URL,WILDCARD")
    sc.add_argument(
        "--include-ineligible",
        action="store_true",
        help="Keep assets not eligible for submission (dropped by default when filtering)",
    )
    sc.add_argument(
        "--targets",
        action="store_true",
        help="Print deduplicated asset identifiers only, one per line (implies --all)",
    )
    sc.set_defaults(func=cmd_scopes)

    wk = sub.add_parser("weaknesses", help="Weaknesses for a program", parents=paged)
    wk.add_argument("handle")
    wk.set_defaults(func=cmd_weaknesses)

    ex = sub.add_parser("exclusions", help="Scope exclusions for a program", parents=[json_p])
    ex.add_argument("handle")
    ex.set_defaults(func=cmd_exclusions)

    bal = sub.add_parser("balance", help="Payment balance", parents=[json_p])
    bal.set_defaults(func=cmd_balance)

    earn = sub.add_parser("earnings", help="Earnings list", parents=paged)
    earn.set_defaults(func=cmd_earnings)

    pay = sub.add_parser("payouts", help="Payouts list", parents=paged)
    pay.set_defaults(func=cmd_payouts)

    hk = sub.add_parser("hacktivity", help="Public hacktivity search", parents=paged)
    hk.add_argument("--query", help="Lucene queryString")
    hk.add_argument("--sort", help="e.g. -disclosed_at")
    hk.set_defaults(func=cmd_hacktivity)

    intents = sub.add_parser("intents", help="Report intents (Report Assistant)")
    isub = intents.add_subparsers(dest="intents_cmd", required=True)
    il = isub.add_parser("list", parents=[json_p])
    il.set_defaults(func=cmd_intents_list)
    ig = isub.add_parser("get", parents=[json_p])
    ig.add_argument("id", type=int)
    ig.set_defaults(func=cmd_intents_get)
    ic = isub.add_parser("create")
    ic.add_argument("--program", required=True)
    ic.add_argument("--description", default="")
    ic.add_argument("--description-file", type=argparse.FileType("r"))
    ic.set_defaults(func=cmd_intents_create)
    iu = isub.add_parser("update")
    iu.add_argument("id", type=int)
    iu.add_argument("--description", default="")
    iu.add_argument("--description-file", type=argparse.FileType("r"))
    iu.set_defaults(func=cmd_intents_update)
    idel = isub.add_parser("delete")
    idel.add_argument("id", type=int)
    idel.add_argument("--confirm", action="store_true")
    idel.set_defaults(func=cmd_intents_delete)
    isubm = isub.add_parser("submit")
    isubm.add_argument("id", type=int)
    isubm.add_argument("--confirm", action="store_true")
    isubm.set_defaults(func=cmd_intents_submit)
    iatt = isub.add_parser("attachments", help="Report intent attachments")
    iasub = iatt.add_subparsers(dest="attachments_cmd", required=True)
    ial = iasub.add_parser("list", help="List attachments of an intent")
    ial.add_argument("id", type=int)
    ial.set_defaults(func=cmd_intents_attachments)
    iad = iasub.add_parser("delete", help="Delete one attachment (requires --confirm)")
    iad.add_argument("id", type=int)
    iad.add_argument("attachment_id", type=int)
    iad.add_argument("--confirm", action="store_true")
    iad.set_defaults(func=cmd_intents_attachment_delete)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        client = H1Client()
    except H1Error as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        return int(args.func(client, args))
    except H1Error as e:
        print(str(e), file=sys.stderr)
        if e.body is not None:
            print(json.dumps(e.body, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
