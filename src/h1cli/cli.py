"""argparse CLI for h1cli."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from . import __version__
from .client import OPEN_STATES, H1Client, H1Error


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _program_handle(item: dict) -> str:
    rel = item.get("relationships") or {}
    prog = ((rel.get("program") or {}).get("data") or {})
    attrs = prog.get("attributes") or {}
    return attrs.get("handle") or prog.get("id") or "-"


def _pages(client: H1Client, args: argparse.Namespace, fetch_page) -> Any:
    """One page by default; every page (as {"data": [...]}) with --all."""
    if getattr(args, "all", False):
        return {"data": client.paginate(fetch_page)}
    return fetch_page(args.page, args.size)


def _trunc(s: str, n: int = 72) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


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
            f"{r.get('id')}\t{a.get('severity_rating') or '-'}\t{prog}\t{_trunc(a.get('title') or '', 60)}"
        )
    return 0


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="h1cli",
        description="CLI for the HackerOne Hacker API (personal token, HTTP Basic).",
    )
    json_p = argparse.ArgumentParser(add_help=False)
    json_p.add_argument("--json", action="store_true", help="Print raw JSON")
    page_p = argparse.ArgumentParser(add_help=False)
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
