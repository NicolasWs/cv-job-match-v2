#!/usr/bin/env python3
"""NIC-56: LinkedIn Saved Jobs -> Notion `selected`-card importer (semi-automated).

Per docs/handoffs/NIC-56-product-planner-scope-validation.md (Option c/d):
Nicolas manually copies his LinkedIn Saved Jobs list from his OWN
already-logged-in browser into a plain-text file or pastes it via stdin.
THIS SCRIPT NEVER MAKES ANY NETWORK CALL TO linkedin.com IN ANY FORM -- it
only reads the manually-provided text and talks to the Notion API (the same
API every other script in this repo uses). There is no browser automation,
no session-cookie handling, and no scraping logic anywhere in this module.

Input contract (Builder's concrete choice for OQ-3 in the scope doc, since
LinkedIn's own saved-jobs copy/paste output is not a stable, machine-parsable
format the Product Planner could specify in advance -- see scope doc SS10/11
risk table, "report, don't guess" mandate):

    One job per non-blank, non-comment line, pipe-delimited:

        Company | Role

    - Lines starting with `#` are treated as comments and ignored.
    - Blank lines are ignored.
    - A line that does not split into exactly two non-empty fields around a
      single `|` is reported as malformed (AC6) -- never guessed, never
      silently dropped, no card is ever created for it.
    - Order in the file is preserved as "most recently saved" order (per
      scope doc SS6): a straight top-to-bottom read of a freshly-copied list.

This is a deliberately narrower, more reliable format than raw freeform
LinkedIn-page paste text (Option c in its purest form); it is Option
c/d's documented, Builder-chosen concrete shape (scope doc SS5 leaves this
choice to Builder, no strong Product Planner preference). Nicolas reformats
his copied list into this one-line-per-job shape before running the script
(a single find/replace or manual retype for a handful of entries is a small
manual step, consistent with the semi-automated scope of this ticket).

Limit / "do all" behavior (AC1):
    - Default: process up to the first 5 *non-duplicate* entries (in input
      order) that pass dedup against existing non-archived Notion cards.
      Any additional non-duplicate entries beyond the first 5 are reported
      as "skipped: exceeds default limit (rerun with --all)" -- NOT created,
      NOT silently dropped, and NOT reported as duplicates (they aren't).
    - `--all`: process every non-duplicate entry, no limit.
    - Duplicate checking always happens first (dedup applies regardless of
      --all), so a later run with --all against a partially-imported batch
      correctly reports the earlier batch's entries as duplicates and only
      creates the genuinely new ones.

Deduplication (AC4): before creating anything, every non-archived card in
the Notion Kanban data source is queried once; an input entry is skipped
(and reported by name) if its Company+Role (case-insensitive, whitespace-
normalized) matches any existing non-archived card's Company+Role,
regardless of that card's current Status. Entries repeated within the same
input batch are also deduplicated against each other (second occurrence
skipped as duplicate).

Card creation: every created card uses the exact same `POST /v1/pages` shape
established by NIC-43 (parent.database_id + properties + children.all in one
call), with `children` ALWAYS produced by
`scripts/notion_job_page_blocks.py`'s `build_job_page_children()` -- no
alternate/invented template. `Name` is `"{Company} - {Role}"` (NIC-48
naming-convention precedent). `Priority` is left unset (scope doc SS7).

No Notion SDK dependency: pure `urllib.request`, matching this repo's
existing `notion_*.py` scripts. Requires the `NOTION_API_KEY` environment
variable (same credential used throughout this repo's Notion tooling).
Never logs or prints the key itself.

Usage as a library:
    from notion_import_saved_jobs import process_entries

    report = process_entries(text, do_all=False, limit=5)
    # report["created"], report["skipped_duplicates"],
    # report["skipped_limit"], report["malformed"]

CLI:
    python3 scripts/notion_import_saved_jobs.py <input_file> [--all]
    python3 scripts/notion_import_saved_jobs.py -            # read stdin
    python3 scripts/notion_import_saved_jobs.py <input_file> --all
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

from notion_job_page_blocks import build_job_page_children

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

DATABASE_ID = "dc98669c-8b63-4f20-b6c0-abdafe8222c6"
DATA_SOURCE_ID = "47340a66-9e15-4ea1-8edf-45bba44c2334"

DEFAULT_LIMIT = 5

# Zero references to any linkedin.com host anywhere in this module's logic
# or network calls (AC5/AC8) -- the only network calls this module ever
# makes are to api.notion.com, below.


def _api_key() -> str:
    key = os.environ.get("NOTION_API_KEY")
    if not key:
        raise RuntimeError("NOTION_API_KEY environment variable is not set")
    return key


def _request(method: str, url: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {err_body}") from None


# ---------------------------------------------------------------------------
# Parsing (AC1, AC6)
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Case-insensitive, whitespace-normalized comparison key."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def parse_entries(text: str) -> tuple:
    """Parses the pipe-delimited input contract described in the module
    docstring. Returns (parsed, malformed):

        parsed:    [{"company": str, "role": str, "raw_line": str, "line_no": int}, ...]
        malformed: [{"raw_line": str, "line_no": int, "reason": str}, ...]

    Never guesses/fabricates a missing field -- any line that doesn't cleanly
    split into exactly two non-empty fields is reported as malformed, not
    silently dropped or filled in (AC6).
    """
    parsed = []
    malformed = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        if len(fields) != 2:
            malformed.append({
                "raw_line": raw_line,
                "line_no": line_no,
                "reason": (
                    f"expected exactly one '|' separator giving 'Company | Role', "
                    f"found {len(fields) - 1} separator(s)"
                ),
            })
            continue
        company, role = fields[0].strip(), fields[1].strip()
        if not company and not role:
            malformed.append({"raw_line": raw_line, "line_no": line_no, "reason": "missing company and role"})
            continue
        if not company:
            malformed.append({"raw_line": raw_line, "line_no": line_no, "reason": "missing company"})
            continue
        if not role:
            malformed.append({"raw_line": raw_line, "line_no": line_no, "reason": "missing role"})
            continue
        parsed.append({"company": company, "role": role, "raw_line": raw_line, "line_no": line_no})
    return parsed, malformed


# ---------------------------------------------------------------------------
# Dedup (AC4)
# ---------------------------------------------------------------------------

def query_all_non_archived_cards() -> list:
    """POST /v1/data_sources/{id}/query with no filter, paginated. Notion
    excludes archived pages from query results by construction, so this
    naturally only returns non-archived cards."""
    results = []
    cursor = None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        resp = _request("POST", f"{NOTION_API_BASE}/data_sources/{DATA_SOURCE_ID}/query", body=body)
        results.extend(resp.get("results", []))
        if resp.get("has_more"):
            cursor = resp.get("next_cursor")
        else:
            break
    return results


def _rich_text_plain(prop: dict) -> str:
    return "".join(rt.get("plain_text", rt.get("text", {}).get("content", "")) for rt in prop.get("rich_text", []))


def build_dedup_index(pages: list) -> dict:
    """Returns {(normalized_company, normalized_role): page_id} for every
    existing non-archived card that has both Company and Role populated."""
    index = {}
    for page in pages:
        props = page.get("properties", {})
        company = _rich_text_plain(props.get("Company", {}))
        role = _rich_text_plain(props.get("Role", {}))
        if company and role:
            index[(normalize(company), normalize(role))] = page.get("id")
    return index


# ---------------------------------------------------------------------------
# Card creation
# ---------------------------------------------------------------------------

def create_selected_card(company: str, role: str) -> dict:
    """POST /v1/pages -- parent.database_id + properties + children (from
    build_job_page_children(), NIC-43's established template) in one call.
    Status is always 'selected'. Priority left unset per scope doc SS7."""
    name = f"{company} - {role}"
    body = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": name}}]},
            "Status": {"status": {"name": "selected"}},
            "Company": {"rich_text": [{"text": {"content": company}}]},
            "Role": {"rich_text": [{"text": {"content": role}}]},
        },
        "children": build_job_page_children(),
    }
    return _request("POST", f"{NOTION_API_BASE}/pages", body=body)


def archive_page(page_id: str) -> dict:
    return _request("PATCH", f"{NOTION_API_BASE}/pages/{page_id}", body={"archived": True})


def get_page(page_id: str) -> dict:
    return _request("GET", f"{NOTION_API_BASE}/pages/{page_id}")


def get_block_children(page_id: str) -> list:
    resp = _request("GET", f"{NOTION_API_BASE}/blocks/{page_id}/children")
    return resp.get("results", [])


# ---------------------------------------------------------------------------
# Orchestration (AC1 limit/all + AC4 dedup, applied together)
# ---------------------------------------------------------------------------

def process_entries(text: str, do_all: bool = False, limit: int = DEFAULT_LIMIT) -> dict:
    """End-to-end: parse -> dedup against existing Notion cards (and within
    this batch) -> apply the default-5-unless-all limit -> create cards for
    the remainder, in input order.

    Returns a report dict:
        {
          "created": [{"company", "role", "page_id", "url"}, ...],
          "skipped_duplicates": [{"company", "role", "raw_line", "line_no", "matched_page_id"}, ...],
          "skipped_limit": [{"company", "role", "raw_line", "line_no"}, ...],
          "malformed": [{"raw_line", "line_no", "reason"}, ...],
          "do_all": bool,
          "limit": int,
        }
    """
    parsed, malformed = parse_entries(text)

    existing_pages = query_all_non_archived_cards()
    dedup_index = build_dedup_index(existing_pages)

    non_duplicates = []
    skipped_duplicates = []
    seen_this_batch = set()
    for entry in parsed:
        key = (normalize(entry["company"]), normalize(entry["role"]))
        if key in dedup_index:
            skipped_duplicates.append({**entry, "matched_page_id": dedup_index[key]})
            continue
        if key in seen_this_batch:
            skipped_duplicates.append({**entry, "matched_page_id": None, "note": "duplicate within this input batch"})
            continue
        seen_this_batch.add(key)
        non_duplicates.append(entry)

    if do_all:
        to_create, skipped_limit = non_duplicates, []
    else:
        to_create, skipped_limit = non_duplicates[:limit], non_duplicates[limit:]

    created = []
    for entry in to_create:
        response = create_selected_card(entry["company"], entry["role"])
        created.append({
            "company": entry["company"],
            "role": entry["role"],
            "page_id": response["id"],
            "url": response.get("url"),
        })

    return {
        "created": created,
        "skipped_duplicates": skipped_duplicates,
        "skipped_limit": skipped_limit,
        "malformed": malformed,
        "do_all": do_all,
        "limit": limit,
    }


def format_report(report: dict) -> str:
    lines = []
    lines.append(f"Created {len(report['created'])} card(s):")
    for c in report["created"]:
        lines.append(f"  - {c['company']} - {c['role']} -> {c['page_id']} ({c['url']})")
    lines.append(f"Skipped {len(report['skipped_duplicates'])} duplicate(s):")
    for d in report["skipped_duplicates"]:
        lines.append(f"  - {d['company']} - {d['role']} (already exists as page {d.get('matched_page_id')})")
    lines.append(f"Skipped {len(report['skipped_limit'])} entrie(s) beyond the default limit of {report['limit']} (rerun with --all):")
    for s in report["skipped_limit"]:
        lines.append(f"  - {s['company']} - {s['role']}")
    lines.append(f"Malformed {len(report['malformed'])} line(s) (not created, not guessed):")
    for m in report["malformed"]:
        lines.append(f"  - line {m['line_no']}: {m['raw_line']!r} -- {m['reason']}")
    return "\n".join(lines)


def _main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    source = sys.argv[1]
    do_all = "--all" in sys.argv[2:]

    if source == "-":
        text = sys.stdin.read()
    else:
        with open(source, "r", encoding="utf-8") as f:
            text = f.read()

    report = process_entries(text, do_all=do_all)
    print(format_report(report))
    print()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    _main()
