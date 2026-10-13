"""Output helpers shared by command handlers."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .client import H1Client


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _program_handle(item: dict) -> str:
    rel = item.get("relationships") or {}
    prog = ((rel.get("program") or {}).get("data") or {})
    attrs = prog.get("attributes") or {}
    return attrs.get("handle") or prog.get("id") or "-"


def _trunc(s: str, n: int = 72) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _pages(client: H1Client, args: argparse.Namespace, fetch_page) -> Any:
    """One page by default; every page (as {"data": [...]}) with --all."""
    if getattr(args, "all", False):
        return {"data": client.paginate(fetch_page)}
    return fetch_page(args.page, args.size)
