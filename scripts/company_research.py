#!/usr/bin/env python3
"""NIC-49: company/website summary formatting, validation, and
non-fabrication-fallback logic for the `company-research` skill.

Per Product Planner scope validation
(docs/handoffs/NIC-49-product-planner-scope-validation.md, section 4,
Option (b)), this module performs NO network calls of its own. The
calling agent (a Claude Code/Hermes session with its own web_search/
web_extract/browser tools) is responsible for:
  1. identifying the company's official website,
  2. fetching its content,
  3. passing the raw text, its source URL, and a retrieval date into
     `build_company_summary()`.

This module's job is the deterministic, unit-testable part: formatting
a 3-5 sentence summary from already-fetched source text, validating the
output shape, and constructing the fixed-shape non-fabrication failure
object when no genuine summary can be built. Pure standard library —
the only imports are `re` and `urllib.parse`. No network calls. No
Notion API calls or Notion-module imports (AC8).

Usage:
    from company_research import build_company_summary

    result = build_company_summary(
        company_name="Acme Corp",
        source_text="<raw text fetched by the calling agent>",
        source_url="https://acme.com/about",
        retrieved_date="2026-09-12",
    )
    # -> {"company_name": "Acme Corp", "summary": "...", "source_url": ...,
    #     "retrieved_date": "2026-09-12", "status": "ok"}

Simulating a failure (the calling agent could not find/fetch a site at
all — see SKILL.md for when this path is used):
    result = build_company_summary(
        company_name="Acme Corp",
        source_text=None,
        source_url=None,
        retrieved_date="2026-09-12",
        not_found_reason="Could not identify an official company website for 'Acme Corp'.",
    )
    # -> {"company_name": "Acme Corp", "summary": None, "source_url": None,
    #     "retrieved_date": "2026-09-12", "status": "not_found",
    #     "reason": "Could not identify an official company website for 'Acme Corp'."}
"""
import re
from typing import Optional
from urllib.parse import urlparse

# Closed enum for the `status` field (scope doc section 5/7).
STATUS_OK = "ok"
STATUS_NOT_FOUND = "not_found"
STATUS_INSUFFICIENT_CONTENT = "insufficient_content"
_VALID_STATUSES = (STATUS_OK, STATUS_NOT_FOUND, STATUS_INSUFFICIENT_CONTENT)

# Sentence count bounds -- hard, mechanical gate per scope doc AC2/OQ-2.
_MIN_SENTENCES = 3
_MAX_SENTENCES = 5

# Minimum raw source_text length (characters, after whitespace collapse)
# below which content is considered too thin to summarize honestly rather
# than fabricate padding. This is a deliberately conservative floor: real
# "About" pages routinely run to several hundred characters; a stub page
# under this floor almost never contains enough genuine content for even
# a 3-sentence, non-padded summary. Documented here as the exact,
# reproducible rule AC4's "insufficient content" unit test exercises.
_MIN_SOURCE_TEXT_LENGTH = 80

# Sentence-splitting rule (documented per AC2): split on a run of one or
# more `.`, `!`, or `?` followed by whitespace or end-of-string. This is a
# simple, deterministic, reproducible rule -- it does not attempt full
# NLP sentence segmentation (e.g. it does not special-case "Mr." or
# "U.S."), matching the precision level of this repo's existing
# formatting helpers (e.g. NIC-48's regex-based sanitization).
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list:
    """Splits `text` into sentences using the documented rule above.

    Trims the input first, then splits on sentence-ending punctuation
    followed by whitespace. Empty fragments (e.g. from trailing
    punctuation) are dropped. Returns a list of non-empty sentence
    strings, each stripped of surrounding whitespace.
    """
    stripped = text.strip()
    if not stripped:
        return []
    parts = _SENTENCE_SPLIT_PATTERN.split(stripped)
    return [p.strip() for p in parts if p.strip()]


def _is_valid_absolute_url(url) -> bool:
    """Returns True if `url` is a syntactically valid absolute http(s)
    URL, per AC3's `urllib.parse`-based check.
    """
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _build_failure(company_name: str, retrieved_date: str, status: str, reason: str) -> dict:
    """Constructs the fixed-shape non-fabrication failure object (scope
    doc section 5/7): `summary` and `source_url` are always null, `status`
    is one of the closed enum values, `reason` is a non-empty human-
    readable string. Never fabricates filler content.
    """
    if status not in (STATUS_NOT_FOUND, STATUS_INSUFFICIENT_CONTENT):
        raise ValueError(
            f"Invalid failure status {status!r}; must be one of "
            f"{(STATUS_NOT_FOUND, STATUS_INSUFFICIENT_CONTENT)!r}."
        )
    if not reason or not reason.strip():
        raise ValueError("reason must be a non-empty string for a failure result.")
    return {
        "company_name": company_name,
        "summary": None,
        "source_url": None,
        "retrieved_date": retrieved_date,
        "status": status,
        "reason": reason,
    }


def build_company_summary(
    company_name: str,
    source_text: Optional[str],
    source_url: Optional[str],
    retrieved_date: str,
    job_url: Optional[str] = None,
    company_website_url: Optional[str] = None,
    not_found_reason: Optional[str] = None,
) -> dict:
    """Builds the company/website summary output contract (scope doc
    section 5). Performs NO network calls -- `source_text`/`source_url`
    must already have been fetched by the calling agent via its own
    web_search/web_extract/browser tools.

    Parameters:
        company_name: required. The company being researched.
        source_text: required for the success path -- raw text already
            fetched by the calling agent from the company's official
            website. Pass None (and set `not_found_reason`) when the
            calling agent could not identify/access any official site
            at all -- this signals the "not_found" path explicitly
            rather than the caller improvising a status string.
        source_url: required for the success path -- the URL
            `source_text` came from. Pass None alongside `source_text=None`
            for the "not_found" path.
        retrieved_date: required, ISO 8601 date string, supplied by the
            calling agent at fetch time (this function does not read the
            system clock -- it only formats/validates what it's given).
        job_url: optional, disambiguation hint only -- not otherwise used
            by this function; accepted so callers can pass it through
            uniformly without a shape mismatch. Never sent anywhere.
        company_website_url: optional, disambiguation hint only -- same
            as `job_url`, accepted but not otherwise used by this
            function's own logic.
        not_found_reason: required when `source_text` is None -- the
            calling agent's reason the site could not be identified or
            accessed at all (fetch blocked, no official site found,
            login-walled, etc.). Ignored when `source_text` is provided.

    Returns the output dict per the exact success/failure shapes in
    scope doc section 5. `status` is one of "ok" | "not_found" |
    "insufficient_content".

    Raises `ValueError` for a malformed call (missing `company_name`/
    `retrieved_date`, or `source_text` given without a valid
    `source_url`) -- this function does not silently guess required
    fields, consistent with this codebase's "fail loudly" style
    (`build_attachment_filename`'s `kind` validation).
    """
    if not company_name or not str(company_name).strip():
        raise ValueError("company_name is required and must be non-empty.")
    if not retrieved_date or not str(retrieved_date).strip():
        raise ValueError("retrieved_date is required and must be non-empty.")

    # --- "not_found" path: the calling agent never obtained any source
    # text at all (no official site identified/accessible). ---
    if source_text is None:
        if not not_found_reason or not not_found_reason.strip():
            raise ValueError(
                "not_found_reason is required and must be non-empty when "
                "source_text is None (the 'not_found' path)."
            )
        return _build_failure(company_name, retrieved_date, STATUS_NOT_FOUND, not_found_reason)

    # From here on, the caller claims it has genuine source text -- so a
    # source_url is mandatory (never fabricate a citation).
    if not _is_valid_absolute_url(source_url):
        raise ValueError(
            f"source_url must be a valid absolute http(s) URL when source_text "
            f"is provided; got {source_url!r}."
        )

    # --- "insufficient_content" path: content fetched, but too thin to
    # honestly summarize (never pad/fabricate). ---
    collapsed = re.sub(r"\s+", " ", source_text).strip()
    if len(collapsed) < _MIN_SOURCE_TEXT_LENGTH:
        return _build_failure(
            company_name,
            retrieved_date,
            STATUS_INSUFFICIENT_CONTENT,
            f"Fetched content from {source_url!r} is too thin/generic "
            f"({len(collapsed)} characters after whitespace collapse) to "
            f"build a genuine summary for '{company_name}' without fabricating.",
        )

    sentences = _split_sentences(collapsed)
    if len(sentences) < _MIN_SENTENCES:
        return _build_failure(
            company_name,
            retrieved_date,
            STATUS_INSUFFICIENT_CONTENT,
            f"Fetched content from {source_url!r} contains only "
            f"{len(sentences)} sentence(s) -- fewer than the minimum "
            f"{_MIN_SENTENCES} needed to build a genuine summary for "
            f"'{company_name}' without fabricating or padding.",
        )

    # Take the first _MAX_SENTENCES sentences verbatim (no rewriting, no
    # paraphrasing, no invented content) -- this keeps the summary
    # strictly grounded in the fetched source text. If more than
    # _MAX_SENTENCES sentences are available, only the first
    # _MAX_SENTENCES are kept; this never fabricates content, it only
    # trims.
    kept = sentences[:_MAX_SENTENCES]
    summary = " ".join(kept)

    return {
        "company_name": company_name,
        "summary": summary,
        "source_url": source_url,
        "retrieved_date": retrieved_date,
        "status": STATUS_OK,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print(__doc__)
        print(
            "Usage: python3 scripts/company_research.py <company_name> "
            "<source_url> <retrieved_date> [source_text_file]"
        )
        sys.exit(1)

    company_arg = sys.argv[1]
    source_url_arg = sys.argv[2]
    retrieved_date_arg = sys.argv[3]

    if len(sys.argv) > 4:
        with open(sys.argv[4], "r", encoding="utf-8") as fh:
            source_text_arg = fh.read()
    else:
        source_text_arg = sys.stdin.read()

    import json as _json

    print(
        _json.dumps(
            build_company_summary(
                company_name=company_arg,
                source_text=source_text_arg,
                source_url=source_url_arg,
                retrieved_date=retrieved_date_arg,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
