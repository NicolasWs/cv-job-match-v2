#!/usr/bin/env python3
"""NIC-50: company-research skill -- recent YouTube video lookup.

Per docs/handoffs/NIC-50-product-planner-scope.md (Product Planner scope,
approved), this module implements the "recent YouTube video about a
company" capability as a standalone, independently-testable unit (AC8).
It is deliberately NOT wired into any `.claude/skills/company-research/`
scaffold -- that scaffold is NIC-49's responsibility (a separate,
still-in-progress ticket); this ticket ships only the logic + a CLI that
an agent (Claude Code / Hermes session) drives using its own general
web-search/browsing tools.

Search mechanism (AC1) -- general web search/browsing ONLY, no YouTube
Data API, no new Apify actor, no new credential of any kind:

    This module makes ZERO network calls itself. It cannot: an agent
    session's `web_search`/`web_extract` MCP tools are not importable as a
    plain Python library from inside a subprocess. Per the scope doc's own
    explicit engineering-judgment call (SS8.2, and the Builder handoff
    instructions), the correct shape for this constraint is:

      1. The AGENT (not this script) runs the two-query search procedure
         documented below (`build_channel_discovery_query()` /
         `build_recent_content_query()`) via its own web_search/web_extract
         tools.
      2. The agent extracts each candidate video's title/url/channel/date
         text from the search results and/or the video's own page (fetched
         via web_extract) and assembles them into a small JSON list.
      3. That JSON is fed into this module's pure functions (importable, or
         via the CLI below) to do the actual recency filtering (AC2),
         no-fabrication date-confirmation gate (AC5), disambiguation
         scoring (AC6), best-candidate selection, and exact-contract
         markdown formatting (AC3/AC4/AC7).

    This keeps all the *logic* (which is what benefits from being tested,
    versioned, and reused) in ordinary, dependency-free Python, while the
    actual internet access stays exactly where the approved architecture
    (PRD OQ-3) says it must: general web search/browsing tool calls made by
    the agent, never a keyed API client living inside this repo.

Recency rule (AC2): a candidate qualifies only if its publish date is
within the last 6 MONTHS of "today" (the date the lookup is run), per
NIC-31's resolution of OQ-14 -- NOT the stale 12-month text still present
in NIC-50's own Linear ticket description or in docs/PRD.md's OQ-14 entry
(both are known documentation-drift issues, see the scope doc SS3). The
window is inclusive of the boundary (a video published exactly 6 calendar
months before "today" still qualifies; one day older does not).

No-fabrication rule (AC5): if a candidate's publish date cannot be parsed
into a confirmed, absolute calendar date, it is EXCLUDED from
consideration entirely -- never guessed, never treated as "probably
recent". This explicitly includes relative-date strings such as
"2 months ago" / "3 weeks ago" -- per the scope doc's own risk table
(SS9), these are frequently tied to the search engine's crawl time, not
the video's real upload time, and are therefore not treated as confirmed
dates by this module under any circumstance.

Output contract (AC3/AC4/AC7), verbatim, exactly as specified in the scope
doc SS8.3 -- do not paraphrase:

    Hit:  **Recent YouTube video:** [<title>](<url>) -- <channel name>, published <publish date>
    Miss: **Recent YouTube video:** no recent video found

Usage as a library (the AC8-required standalone, independently-testable
entry point -- just a company name plus already-fetched candidate data,
no dependency on any other ticket's unshipped code):

    from company_research_youtube_video import run_lookup

    raw_candidates = [
        {"title": "...", "url": "https://youtube.com/watch?v=...",
         "channel": "...", "date_text": "2026-05-14"},
        ...
    ]
    snippet = run_lookup(raw_candidates, company="Acme Corp", domain="acme.com")
    print(snippet)

CLI:
    python3 scripts/company_research_youtube_video.py \
        --company "Acme Corp" [--domain acme.com] \
        --candidates /path/to/candidates.json [--today 2026-09-12]

    (--today is provided only for deterministic testing of the recency
    boundary; when omitted, the real current date is used.)
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

RECENCY_WINDOW_MONTHS = 6  # NIC-31 resolution of OQ-14 -- 6 months, not 12.

MISS_LINE = "**Recent YouTube video:** no recent video found"


# ---------------------------------------------------------------------------
# Search procedure (AC1) -- documented queries the AGENT runs via its own
# web_search/web_extract tools. This module does not call them itself.
# ---------------------------------------------------------------------------

def build_channel_discovery_query(company: str) -> str:
    """Query 1 (channel discovery), per scope doc SS6 step 1."""
    return f'"{company}" official YouTube channel'


def build_recent_content_query(company: str) -> str:
    """Query 2 (recent-content discovery), per scope doc SS6 step 2."""
    return f'"{company}" (interview OR "product demo" OR culture OR announcement) site:youtube.com'


# ---------------------------------------------------------------------------
# Date parsing -- confirmed-absolute-date-only, no relative-date guessing
# (AC5).
# ---------------------------------------------------------------------------

_MONTHS = (
    "january february march april may june july august september "
    "october november december"
).split()
_MONTH_ABBR = [m[:3] for m in _MONTHS]

# Absolute-date formats this module is willing to trust as "confirmed".
# All require a full, unambiguous year -- nothing relative, nothing
# assumed.
_ABSOLUTE_DATE_FORMATS = [
    "%Y-%m-%d",           # 2026-05-14
    "%Y/%m/%d",           # 2026/05/14
    "%B %d, %Y",          # May 14, 2026
    "%b %d, %Y",          # May 14, 2026 (abbreviated)
    "%d %B %Y",           # 14 May 2026
    "%d %b %Y",           # 14 May 2026 (abbreviated)
    "%B %d %Y",           # May 14 2026 (no comma)
    "%b %d %Y",           # May 14 2026 (no comma, abbreviated)
]

_ISO_DATETIME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ]\d{2}:\d{2}:\d{2}"
)

# Explicit reject list -- relative/ambiguous date phrasing that must NEVER
# be treated as confirmed, even though it superficially "looks like a
# date" in a search snippet. Documented, not silently handled.
_RELATIVE_DATE_MARKERS = (
    "ago", "yesterday", "today", "just now", "streamed live", "live now",
)


def parse_publish_date(raw_text: Optional[str]) -> tuple[Optional[date], bool]:
    """Attempts to parse `raw_text` into a confirmed, absolute calendar
    date.

    Returns (parsed_date_or_None, confirmed: bool). `confirmed` is False
    whenever the date cannot be resolved to an unambiguous absolute date
    -- callers (see `filter_recent_candidates`) MUST exclude any candidate
    with `confirmed == False` rather than guessing (AC5). This includes,
    deliberately, relative-date strings like "2 months ago" that search
    snippets commonly show: those are frequently anchored to crawl time,
    not the video's real upload time (scope doc SS9 risk), so they are
    never trusted here regardless of how "close" they might seem.
    """
    if not raw_text or not raw_text.strip():
        return None, False

    text = raw_text.strip()
    lowered = text.lower()

    for marker in _RELATIVE_DATE_MARKERS:
        if marker in lowered:
            return None, False

    # Strip common non-date prefixes that YouTube pages/snippets attach
    # (e.g. "Premiered May 14, 2026", "Streamed on May 14, 2026").
    cleaned = re.sub(
        r"^(premiered|published|uploaded|streamed( live)? on)\s*:?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    iso_match = _ISO_DATETIME_RE.match(cleaned)
    if iso_match:
        cleaned = iso_match.group(1)

    for fmt in _ABSOLUTE_DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            return parsed, True
        except ValueError:
            continue

    return None, False


# ---------------------------------------------------------------------------
# Recency window (AC2), inclusive boundary, real calendar-month arithmetic
# (not a naive "182 days" approximation).
# ---------------------------------------------------------------------------

def subtract_months(d: date, months: int) -> date:
    """Returns the calendar date `months` months before `d`, clamping the
    day-of-month if the target month is shorter (e.g. Mar 31 - 1 month ->
    Feb 28/29, not Mar 3)."""
    total_month_index = (d.year * 12 + (d.month - 1)) - months
    year, month0 = divmod(total_month_index, 12)
    month = month0 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def recency_cutoff(today: date, window_months: int = RECENCY_WINDOW_MONTHS) -> date:
    return subtract_months(today, window_months)


def is_within_recency_window(
    published: date, today: date, window_months: int = RECENCY_WINDOW_MONTHS
) -> bool:
    """Inclusive on the near boundary (cutoff date itself qualifies);
    also excludes implausible future-dated candidates (published after
    "today"), which are far more likely a parsing artifact than a real
    time-travelling video."""
    cutoff = recency_cutoff(today, window_months)
    return cutoff <= published <= today


# ---------------------------------------------------------------------------
# Candidate model, disambiguation scoring (AC6), selection.
# ---------------------------------------------------------------------------

@dataclass
class VideoCandidate:
    title: str
    url: str
    channel: str
    raw_date_text: str = ""
    published_date: Optional[date] = None
    date_confirmed: bool = False
    company_match_score: int = 0
    rejection_reason: Optional[str] = field(default=None)


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _domain_slug(domain: str) -> str:
    """Very small heuristic: 'mistral.ai' -> 'mistral', 'www.acme.com' ->
    'acme'. Not a full public-suffix-list implementation -- good enough
    for the disambiguation *signal* this capability needs (a bonus score
    contributor, never the sole gate), per scope doc AC6."""
    domain = domain.lower().strip()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]
    parts = domain.split(".")
    return parts[0] if parts else domain


def score_company_match(
    candidate: VideoCandidate, company: str, domain: Optional[str] = None
) -> int:
    """Company-identity disambiguation score (AC6). Company name is
    always the primary signal (channel/title matching against it); the
    optional website domain is used only as a supplementary
    disambiguation signal on top of that, exactly as the scope doc
    specifies ("job URL/website URL ... used only for disambiguation, not
    as a substitute for a distinct company-name field")."""
    score = 0
    norm_company = _normalize(company)
    norm_channel = _normalize(candidate.channel)
    norm_title = _normalize(candidate.title)
    company_tokens = set(norm_company.split())

    if norm_company and norm_company == norm_channel:
        score += 5
    elif norm_company and norm_company in norm_channel:
        score += 3
    elif company_tokens and company_tokens & set(norm_channel.split()):
        score += 1

    if norm_company and norm_company in norm_title:
        score += 2

    if domain:
        slug = _domain_slug(domain)
        if slug and len(slug) >= 3:
            haystacks = (
                norm_channel.replace(" ", ""),
                candidate.url.lower(),
            )
            if any(slug in h for h in haystacks):
                score += 4

    return score


def build_candidates(raw_candidates: list[dict]) -> list[VideoCandidate]:
    """Converts agent-supplied raw search-result dicts (title/url/channel/
    date_text) into VideoCandidate objects with parsed dates. Never raises
    on a missing/unparseable date -- unconfirmed dates are represented,
    not dropped silently, so callers can report on rejections (AC5
    transparency)."""
    candidates = []
    for raw in raw_candidates:
        published, confirmed = parse_publish_date(raw.get("date_text", ""))
        candidates.append(
            VideoCandidate(
                title=raw.get("title", ""),
                url=raw.get("url", ""),
                channel=raw.get("channel", ""),
                raw_date_text=raw.get("date_text", ""),
                published_date=published,
                date_confirmed=confirmed,
            )
        )
    return candidates


def filter_recent_candidates(
    candidates: list[VideoCandidate],
    today: date,
    window_months: int = RECENCY_WINDOW_MONTHS,
) -> list[VideoCandidate]:
    """Applies AC2 (recency window) + AC5 (no-fabrication) together.
    Returns only candidates with a confirmed date that falls within the
    window; every excluded candidate's `rejection_reason` is set for
    evidence/audit purposes (never silently dropped without a reason)."""
    accepted = []
    for c in candidates:
        if not c.date_confirmed or c.published_date is None:
            c.rejection_reason = (
                f"publish date could not be confirmed from {c.raw_date_text!r} "
                "-- excluded rather than guessed (AC5)"
            )
            continue
        if not is_within_recency_window(c.published_date, today, window_months):
            cutoff = recency_cutoff(today, window_months)
            c.rejection_reason = (
                f"published {c.published_date.isoformat()} is outside the "
                f"{window_months}-month window (cutoff {cutoff.isoformat()}, "
                f"today {today.isoformat()})"
            )
            continue
        accepted.append(c)
    return accepted


def select_best_candidate(
    candidates: list[VideoCandidate], company: str, domain: Optional[str] = None
) -> Optional[VideoCandidate]:
    """Selects the single best qualifying candidate: highest
    company-identity match score first (AC6 disambiguation), then most
    recent publish date (scope doc SS6 step 5: "prefer the one most
    clearly about/from the company ... over a tangential mention")."""
    if not candidates:
        return None
    for c in candidates:
        c.company_match_score = score_company_match(c, company, domain)
    return sorted(
        candidates,
        key=lambda c: (c.company_match_score, c.published_date),
        reverse=True,
    )[0]


# ---------------------------------------------------------------------------
# Output formatting (AC3/AC4/AC7) -- exact contract, no paraphrasing.
# ---------------------------------------------------------------------------

def format_hit(candidate: VideoCandidate) -> str:
    assert candidate.published_date is not None, (
        "format_hit() must only be called with a candidate that passed "
        "filter_recent_candidates() (confirmed, in-window publish date)"
    )
    published_str = candidate.published_date.isoformat()
    return (
        f"**Recent YouTube video:** [{candidate.title}]({candidate.url}) "
        f"\u2014 {candidate.channel}, published {published_str}"
    )


def format_miss() -> str:
    return MISS_LINE


def format_result(candidate: Optional[VideoCandidate]) -> str:
    return format_hit(candidate) if candidate is not None else format_miss()


# ---------------------------------------------------------------------------
# End-to-end pipeline (importable, AC8: standalone + independently
# testable with just a company name + already-fetched candidate data).
# ---------------------------------------------------------------------------

def run_lookup(
    raw_candidates: list[dict],
    company: str,
    domain: Optional[str] = None,
    today: Optional[date] = None,
) -> str:
    """Full pipeline: raw agent-supplied search results -> parsed dates ->
    recency+no-fabrication filter -> disambiguation-ranked selection ->
    exact-contract markdown snippet. Returns the markdown string (hit or
    the literal miss string) -- never raw tool output, never a Notion
    call (AC7)."""
    if today is None:
        today = date.today()
    candidates = build_candidates(raw_candidates)
    qualifying = filter_recent_candidates(candidates, today)
    best = select_best_candidate(qualifying, company, domain)
    return format_result(best)


def run_lookup_verbose(
    raw_candidates: list[dict],
    company: str,
    domain: Optional[str] = None,
    today: Optional[date] = None,
) -> dict:
    """Same as run_lookup() but also returns the full accept/reject
    evidence trail (all candidates considered, and why each was accepted
    or rejected) -- used for evidence capture during testing/QA, not part
    of the AC3/AC4 output contract itself."""
    if today is None:
        today = date.today()
    all_candidates = build_candidates(raw_candidates)
    qualifying = filter_recent_candidates(all_candidates, today)
    best = select_best_candidate(qualifying, company, domain)
    snippet = format_result(best)
    return {
        "company": company,
        "domain": domain,
        "today": today.isoformat(),
        "recency_cutoff": recency_cutoff(today).isoformat(),
        "channel_discovery_query": build_channel_discovery_query(company),
        "recent_content_query": build_recent_content_query(company),
        "candidates_considered": [
            {
                "title": c.title,
                "url": c.url,
                "channel": c.channel,
                "raw_date_text": c.raw_date_text,
                "parsed_date": c.published_date.isoformat() if c.published_date else None,
                "date_confirmed": c.date_confirmed,
                "accepted": c in qualifying,
                "rejection_reason": c.rejection_reason,
                "company_match_score": c.company_match_score,
            }
            for c in all_candidates
        ],
        "selected": (
            {
                "title": best.title,
                "url": best.url,
                "channel": best.channel,
                "published_date": best.published_date.isoformat(),
                "company_match_score": best.company_match_score,
            }
            if best is not None
            else None
        ),
        "snippet": snippet,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "NIC-50: filter/rank/format agent-supplied YouTube search "
            "candidates into the recent-video markdown snippet contract. "
            "This CLI does NOT perform any web search itself -- pass in "
            "candidates already gathered by the calling agent's own "
            "web_search/web_extract tool calls."
        )
    )
    parser.add_argument("--company", required=True, help="Company name (primary search/match signal).")
    parser.add_argument("--domain", default=None, help="Optional company website domain, for disambiguation only.")
    parser.add_argument(
        "--candidates",
        required=True,
        help=(
            "Path to a JSON file: a list of "
            '{"title", "url", "channel", "date_text"} objects, or "-" for stdin.'
        ),
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override 'today' as YYYY-MM-DD (testing only; defaults to the real current date).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the full JSON evidence trail (candidates considered, accept/reject reasons) in addition to the snippet.",
    )
    args = parser.parse_args(argv)

    if args.candidates == "-":
        raw_text = sys.stdin.read()
    else:
        with open(args.candidates, "r", encoding="utf-8") as f:
            raw_text = f.read()
    raw_candidates = json.loads(raw_text) if raw_text.strip() else []

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None

    if args.verbose:
        result = run_lookup_verbose(raw_candidates, args.company, args.domain, today)
        print(json.dumps(result, indent=2))
        print()
        print(result["snippet"])
    else:
        print(run_lookup(raw_candidates, args.company, args.domain, today))

    return 0


if __name__ == "__main__":
    sys.exit(_main())
