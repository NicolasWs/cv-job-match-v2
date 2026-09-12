#!/usr/bin/env python3
"""NIC-50 Builder unit tests -- company_research_youtube_video.py.

Covers, per docs/handoffs/NIC-50-product-planner-scope.md §7:
  - AC2: recency boundary (exactly 6 months old = accept, 6 months + 1 day = reject)
  - AC5: no-fabrication (relative date string "2 months ago" excluded, not guessed)
  - AC3: hit-format exactness
  - AC4: miss-format exactness (literal "no recent video found")
  - AC6: disambiguation scoring (company-name-matching channel preferred over
         a same-named-but-different entity, when both otherwise qualify)

Run: python3 scripts/test_company_research_youtube_video.py
Exits 0 and prints "RESULT: ALL TESTS PASSED" on success; exits 1 and prints
the failing assertion otherwise. No network calls, no fabricated evidence --
this is pure logic against the already-implemented module.
"""
import sys
from datetime import date

sys.path.insert(0, "scripts")
from company_research_youtube_video import (  # noqa: E402
    MISS_LINE,
    build_candidates,
    filter_recent_candidates,
    format_hit,
    format_miss,
    format_result,
    parse_publish_date,
    recency_cutoff,
    run_lookup,
    run_lookup_verbose,
    select_best_candidate,
)

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"PASS: {label}")
    else:
        msg = f"FAIL: {label} {detail}".strip()
        print(msg)
        failures.append(msg)


# ---------------------------------------------------------------------
# AC2 -- recency boundary: exactly 6 months old = accept, +1 day = reject
# ---------------------------------------------------------------------
today = date(2026, 9, 12)
cutoff = recency_cutoff(today)
check("AC2 cutoff computed as 2026-03-12", cutoff == date(2026, 3, 12), f"got {cutoff}")

boundary_candidates_raw = [
    {"title": "Exactly at cutoff", "url": "https://youtube.com/watch?v=at-cutoff",
     "channel": "Acme Corp", "date_text": "2026-03-12"},
    {"title": "One day past cutoff", "url": "https://youtube.com/watch?v=past-cutoff",
     "channel": "Acme Corp", "date_text": "2026-03-11"},
]
boundary_candidates = build_candidates(boundary_candidates_raw)
accepted = filter_recent_candidates(boundary_candidates, today)
accepted_urls = {c.url for c in accepted}
check(
    "AC2 exactly-6-months-old (2026-03-12) is ACCEPTED",
    "https://youtube.com/watch?v=at-cutoff" in accepted_urls,
    f"accepted={accepted_urls}",
)
check(
    "AC2 6-months-plus-1-day-old (2026-03-11) is REJECTED",
    "https://youtube.com/watch?v=past-cutoff" not in accepted_urls,
    f"accepted={accepted_urls}",
)
rejected_one_day = [c for c in boundary_candidates if c.url.endswith("past-cutoff")][0]
check(
    "AC2 rejected candidate carries a rejection_reason (audit trail)",
    rejected_one_day.rejection_reason is not None and "outside" in rejected_one_day.rejection_reason,
    f"reason={rejected_one_day.rejection_reason!r}",
)

# ---------------------------------------------------------------------
# AC5 -- no-fabrication: relative date string must be excluded, not guessed
# ---------------------------------------------------------------------
parsed, confirmed = parse_publish_date("2 months ago")
check(
    "AC5 '2 months ago' is NOT confirmed (parsed=None, confirmed=False)",
    parsed is None and confirmed is False,
    f"got parsed={parsed}, confirmed={confirmed}",
)

relative_candidates_raw = [
    {"title": "Relative-dated video", "url": "https://youtube.com/watch?v=relative",
     "channel": "Acme Corp", "date_text": "2 months ago"},
]
relative_candidates = build_candidates(relative_candidates_raw)
relative_accepted = filter_recent_candidates(relative_candidates, today)
check(
    "AC5 candidate with only a relative date is excluded from acceptance",
    len(relative_accepted) == 0,
    f"accepted={relative_accepted}",
)
rc = relative_candidates[0]
check(
    "AC5 excluded candidate's rejection_reason cites unconfirmed date, not recency",
    rc.rejection_reason is not None and "could not be confirmed" in rc.rejection_reason,
    f"reason={rc.rejection_reason!r}",
)
# End-to-end: a company with ONLY a relative-dated candidate must produce the
# miss fallback, not a fabricated hit.
snippet_relative_only = run_lookup(relative_candidates_raw, company="Acme Corp", today=today)
check(
    "AC5 end-to-end run_lookup() falls back to miss when only unconfirmed dates exist",
    snippet_relative_only == MISS_LINE,
    f"got {snippet_relative_only!r}",
)

# ---------------------------------------------------------------------
# AC3 -- hit-format exactness
# ---------------------------------------------------------------------
hit_raw = [
    {"title": "Acme Corp Product Demo 2026", "url": "https://youtube.com/watch?v=abc123",
     "channel": "Acme Corp", "date_text": "2026-05-14"},
]
hit_candidates = build_candidates(hit_raw)
hit_accepted = filter_recent_candidates(hit_candidates, today)
best_hit = select_best_candidate(hit_accepted, company="Acme Corp")
hit_snippet = format_hit(best_hit)
expected_hit = (
    "**Recent YouTube video:** [Acme Corp Product Demo 2026](https://youtube.com/watch?v=abc123) "
    "\u2014 Acme Corp, published 2026-05-14"
)
check(
    "AC3 format_hit() produces exact contract string (title, url, channel, date)",
    hit_snippet == expected_hit,
    f"got {hit_snippet!r}",
)
check(
    "AC3 format_result() dispatches to hit format for a qualifying candidate",
    format_result(best_hit) == expected_hit,
)

# ---------------------------------------------------------------------
# AC4 -- miss-format exactness: literal "no recent video found"
# ---------------------------------------------------------------------
check(
    "AC4 format_miss() is exactly the MISS_LINE constant",
    format_miss() == MISS_LINE,
)
check(
    "AC4 MISS_LINE contains the exact literal substring 'no recent video found'",
    "no recent video found" in MISS_LINE and MISS_LINE.endswith("no recent video found"),
    f"got {MISS_LINE!r}",
)
check(
    "AC4 format_result(None) (zero qualifying candidates) returns the miss line",
    format_result(None) == MISS_LINE,
)
empty_snippet = run_lookup([], company="Nonexistent Co", today=today)
check(
    "AC4 run_lookup() with zero candidates returns the exact miss line",
    empty_snippet == MISS_LINE,
    f"got {empty_snippet!r}",
)

# ---------------------------------------------------------------------
# AC6 -- disambiguation: company-name-matching channel preferred over a
# same-named-but-different entity, both otherwise qualifying (same recency).
# ---------------------------------------------------------------------
# "Acme" the company (channel == "Acme Inc", title mentions "Acme") vs.
# "Acme" a totally unrelated gaming/vlog channel that just happens to have
# been returned by the loose site:youtube.com search query, with a title
# that doesn't reference the company at all.
ambiguous_raw = [
    {
        "title": "Random gaming montage",
        "url": "https://youtube.com/watch?v=unrelated",
        "channel": "AcmeGamerXYZ",  # superficially contains "acme" but not a real match
        "date_text": "2026-06-01",
    },
    {
        "title": "Acme Inc quarterly product announcement",
        "url": "https://youtube.com/watch?v=real-company-video",
        "channel": "Acme Inc",
        "date_text": "2026-05-01",  # older than the other candidate, but should still win
    },
]
ambiguous_candidates = build_candidates(ambiguous_raw)
ambiguous_accepted = filter_recent_candidates(ambiguous_candidates, today)
check(
    "AC6 setup: both ambiguous-test candidates qualify on recency",
    len(ambiguous_accepted) == 2,
    f"accepted={[c.url for c in ambiguous_accepted]}",
)
best_ambiguous = select_best_candidate(ambiguous_accepted, company="Acme Inc")
check(
    "AC6 disambiguation: company/title-matching channel wins over unrelated "
    "same-substring channel even though it is NOT the most recent",
    best_ambiguous is not None and best_ambiguous.url == "https://youtube.com/watch?v=real-company-video",
    f"selected={best_ambiguous.url if best_ambiguous else None}",
)
real_co = [c for c in ambiguous_candidates if c.url.endswith("real-company-video")][0]
unrelated = [c for c in ambiguous_candidates if c.url.endswith("unrelated")][0]
check(
    "AC6 real-company candidate scores strictly higher than the unrelated one",
    real_co.company_match_score > unrelated.company_match_score,
    f"real={real_co.company_match_score} unrelated={unrelated.company_match_score}",
)
ambiguous_snippet = run_lookup(ambiguous_raw, company="Acme Inc", today=today)
check(
    "AC6 end-to-end run_lookup() snippet selects the real-company video",
    "Acme Inc quarterly product announcement" in ambiguous_snippet,
    f"got {ambiguous_snippet!r}",
)

# Sanity: run_lookup_verbose returns the evidence trail with all fields used above.
verbose = run_lookup_verbose(ambiguous_raw, company="Acme Inc", today=today)
check(
    "Sanity: run_lookup_verbose() reports both candidates_considered",
    len(verbose["candidates_considered"]) == 2,
)

print()
if failures:
    print(f"RESULT: {len(failures)} TEST(S) FAILED")
    for f in failures:
        print(" -", f)
    sys.exit(1)
else:
    print("RESULT: ALL TESTS PASSED")
    sys.exit(0)
