# h1cli

CLI for the **HackerOne Hacker API** (personal API token, HTTP Basic auth).

Docs: [Getting started (Hacker API)](https://api.hackerone.com/getting-started-hacker-api/) · [Hacker resources](https://api.hackerone.com/hacker-resources/)

## Install

```bash
pip install -e .
# or
python -m pip install -e /path/to/h1cli
```

Requires Python 3.10+. **No third-party runtime dependencies.**

## Auth

```bash
export HACKERONE_USERNAME='your-h1-username'   # not email
export HACKERONE_API_TOKEN='your-token'
# aliases: H1_USERNAME / H1_API_TOKEN
```

Create a token under HackerOne → Settings → API Token. Never commit tokens.

## Commands

| Command | API |
|---------|-----|
| `h1cli whoami` | smoke `GET /hackers/me/reports` |
| `h1cli reports list [--state open\|STATE] [--program HANDLE]` | `GET /hackers/me/reports` |
| `h1cli reports get ID [--body]` | `GET /hackers/reports/{id}` |
| `h1cli reports create ... --confirm` | `POST /hackers/reports` |
| `h1cli programs list` | `GET /hackers/programs` |
| `h1cli programs get HANDLE [--policy]` | `GET /hackers/programs/{handle}` |
| `h1cli scopes HANDLE [--all] [--bounty-only] [--type URL,WILDCARD] [--targets]` | `GET /hackers/programs/{handle}/structured_scopes` |
| `h1cli weaknesses HANDLE` | `GET /hackers/programs/{handle}/weaknesses` |
| `h1cli exclusions HANDLE` | `GET /hackers/programs/{handle}/scope_exclusions` |
| `h1cli balance` | `GET /hackers/payments/balance` |
| `h1cli earnings` | `GET /hackers/payments/earnings` |
| `h1cli payouts` | `GET /hackers/payments/payouts` |
| `h1cli hacktivity [--query ...] [--sort ...]` | `GET /hackers/hacktivity` |
| `h1cli intents list\|get\|create\|update\|delete\|submit\|attachments` | report intents |

When filtering (`--all`, `--targets`, `--bounty-only`, `--type`), assets not eligible for submission are dropped unless `--include-ineligible` is given.

Destructive / submitting commands require `--confirm`.

### Examples

```bash
h1cli whoami
h1cli reports list --state open
h1cli reports get 4103144 --body
h1cli programs get tron_dao --policy | head
h1cli scopes tron_dao
# export in-scope, bounty-eligible web targets (all pages) for recon tools
h1cli scopes tron_dao --targets --bounty-only --type URL,WILDCARD > targets.txt
h1cli hacktivity --query 'team:tron_dao' --size 10
```

## Out of scope for this CLI (hacker token)

| Feature | Why |
|---------|-----|
| **Webhooks** | Program/organization automation. Configured in program Settings → Automation → Webhooks. Documented under the [Customer/org API webhooks](https://api.hackerone.com/webhooks/), not the Hacker API. A personal hacker token cannot manage them. |
| Organization admin APIs | Members, triage inbox as org, customer report management — need an **organization API token**. |
| Multipart attachment **upload** to report intents | Not implemented yet (stdlib multipart); list/delete attachments are available. |

Rate limits (Hacker API): ~600 reads/min, ~25 writes / 20s.

## License

MIT
