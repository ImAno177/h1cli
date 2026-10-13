"""Minimal HackerOne Hacker API client (stdlib only)."""

from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, MutableMapping, Optional


BASE_URL = "https://api.hackerone.com/v1"
OPEN_STATES = frozenset(
    {
        "new",
        "pending-program-review",
        "triaged",
        "needs-more-info",
        "retesting",
    }
)


def _seg(value: Any) -> str:
    """Encode one URL path segment; '/' and '..' tricks cannot escape it."""
    return urllib.parse.quote(str(value), safe="")


class H1Error(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class H1Client:
    def __init__(
        self,
        username: Optional[str] = None,
        token: Optional[str] = None,
        base_url: str = BASE_URL,
        opener: Any = None,
    ):
        self.username = username or os.environ.get("HACKERONE_USERNAME") or os.environ.get(
            "H1_USERNAME"
        )
        self.token = token or os.environ.get("HACKERONE_API_TOKEN") or os.environ.get(
            "H1_API_TOKEN"
        )
        self.base_url = base_url.rstrip("/")
        self._opener = opener
        if not self.username or not self.token:
            raise H1Error(
                "Set HACKERONE_USERNAME and HACKERONE_API_TOKEN "
                "(or H1_USERNAME / H1_API_TOKEN)."
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            # Support nested page[size] style keys as already-encoded names
            qs = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}, doseq=True
            )
            url = f"{url}?{qs}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        cred = base64.b64encode(f"{self.username}:{self.token}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {cred}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        opener = self._opener or urllib.request.build_opener()
        try:
            with opener.open(req, timeout=60) as resp:
                raw = resp.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body: Any
            try:
                err_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                err_body = None
            if e.code == 401:
                raise H1Error("Unauthorized (401): check username/token.", 401, err_body) from e
            if e.code == 403:
                raise H1Error("Forbidden (403): token lacks access.", 403, err_body) from e
            if e.code == 429:
                raise H1Error("Rate limited (429): slow down.", 429, err_body) from e
            raise H1Error(f"HTTP {e.code}: {e.reason}", e.code, err_body) from e

    def get(self, path: str, **params: Any) -> Any:
        return self._request("GET", path, params=params or None)

    def post(self, path: str, body: Mapping[str, Any]) -> Any:
        return self._request("POST", path, body=body)

    def patch(self, path: str, body: Mapping[str, Any]) -> Any:
        return self._request("PATCH", path, body=body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # --- Reports ---
    def list_reports(self, page: int = 1, size: int = 25) -> Any:
        return self.get("/hackers/me/reports", **{"page[number]": page, "page[size]": size})

    def get_report(self, report_id: int | str) -> Any:
        return self.get(f"/hackers/reports/{_seg(report_id)}")

    def create_report(self, attributes: Mapping[str, Any]) -> Any:
        return self.post(
            "/hackers/reports",
            {"data": {"type": "report", "attributes": dict(attributes)}},
        )

    # --- Programs ---
    def list_programs(self, page: int = 1, size: int = 25) -> Any:
        return self.get("/hackers/programs", **{"page[number]": page, "page[size]": size})

    def get_program(self, handle: str) -> Any:
        return self.get(f"/hackers/programs/{_seg(handle)}")

    def structured_scopes(self, handle: str, page: int = 1, size: int = 25) -> Any:
        return self.get(
            f"/hackers/programs/{_seg(handle)}/structured_scopes",
            **{"page[number]": page, "page[size]": size},
        )

    def all_structured_scopes(self, handle: str, size: int = 100, max_pages: int = 50) -> list:
        """Fetch every structured scope for a program, following pagination."""
        items: list = []
        for page in range(1, max_pages + 1):
            data = self.structured_scopes(handle, page=page, size=size) or {}
            batch = list(data.get("data") or [])
            items.extend(batch)
            if not (data.get("links") or {}).get("next") or not batch:
                break
        return items

    def weaknesses(self, handle: str, page: int = 1, size: int = 25) -> Any:
        return self.get(
            f"/hackers/programs/{_seg(handle)}/weaknesses",
            **{"page[number]": page, "page[size]": size},
        )

    def scope_exclusions(self, handle: str) -> Any:
        return self.get(f"/hackers/programs/{_seg(handle)}/scope_exclusions")

    # --- Payments ---
    def balance(self) -> Any:
        return self.get("/hackers/payments/balance")

    def earnings(self, page: int = 1, size: int = 25) -> Any:
        return self.get(
            "/hackers/payments/earnings", **{"page[number]": page, "page[size]": size}
        )

    def payouts(self, page: int = 1, size: int = 25) -> Any:
        return self.get(
            "/hackers/payments/payouts", **{"page[number]": page, "page[size]": size}
        )

    # --- Hacktivity ---
    def hacktivity(
        self,
        query: Optional[str] = None,
        sort: Optional[str] = None,
        page: int = 1,
        size: int = 25,
    ) -> Any:
        params: MutableMapping[str, Any] = {"page[number]": page, "page[size]": size}
        if query:
            params["queryString"] = query
        if sort:
            params["sort"] = sort
        return self.get("/hackers/hacktivity", **params)

    # --- Report intents ---
    def list_report_intents(self) -> Any:
        return self.get("/hackers/report_intents")

    def get_report_intent(self, intent_id: int | str) -> Any:
        return self.get(f"/hackers/report_intents/{_seg(intent_id)}")

    def create_report_intent(self, team_handle: str, description: str) -> Any:
        return self.post(
            "/hackers/report_intents",
            {
                "data": {
                    "type": "report-intent",
                    "attributes": {
                        "team_handle": team_handle,
                        "description": description,
                    },
                }
            },
        )

    def update_report_intent(self, intent_id: int | str, description: str) -> Any:
        return self.patch(
            f"/hackers/report_intents/{_seg(intent_id)}",
            {
                "data": {
                    "type": "report-intent",
                    "attributes": {"description": description},
                }
            },
        )

    def delete_report_intent(self, intent_id: int | str) -> Any:
        return self.delete(f"/hackers/report_intents/{_seg(intent_id)}")

    def submit_report_intent(self, intent_id: int | str) -> Any:
        return self.post(f"/hackers/report_intents/{_seg(intent_id)}/submit", {})

    def list_intent_attachments(self, intent_id: int | str) -> Any:
        return self.get(f"/hackers/report_intents/{_seg(intent_id)}/attachments")

    def delete_intent_attachment(self, intent_id: int | str, attachment_id: int | str) -> Any:
        return self.delete(f"/hackers/report_intents/{_seg(intent_id)}/attachments/{_seg(attachment_id)}")
