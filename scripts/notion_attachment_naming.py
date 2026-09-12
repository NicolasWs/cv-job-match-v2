#!/usr/bin/env python3
"""NIC-48: shared filename-builder helper for Notion job-page attachments.

Per Product Planner scope validation
(docs/handoffs/NIC-48-product-planner-scope-validation.md, section 4-5),
this module formalizes the `{Company} - {Role} - {Kind}.{ext}` naming
convention (FR-E3, US-7) with a concrete, unit-testable sanitization rule,
WITHOUT modifying either already-shipped, QA-passed attachment mechanism
(`scripts/notion_cv_attachment.py`, `scripts/notion_cover_letter_attachment.py`).
Callers of `attach_final_cv()` / `attach_final_cover_letter()` are expected
to compute their `filename` argument via `build_attachment_filename()`
instead of hand-typing a string.

Pure standard library, no network calls, no dependency on either
attachment script (naming has no reason to import attachment logic).

Usage:
    from notion_attachment_naming import build_attachment_filename

    filename = build_attachment_filename("Acme", "Backend Engineer", "CV")
    # -> "Acme - Backend Engineer - CV.pdf"
"""
import re

# Closed set of valid `kind` values -- exact display strings used in the
# final filename. Distinct from the heading-text constants
# (TAILORED_CV_HEADING / COVER_LETTER_HEADING) in the attachment scripts,
# which are Notion block headings, not filenames -- must not be conflated
# (per scope doc section 4).
VALID_KINDS = ("CV", "Cover Letter")

# Windows-reserved filesystem-unsafe character set (scope doc section 5,
# step 3) -- the strictest common denominator so filenames stay portable
# across macOS/Linux/Windows even though Notion itself is not a filesystem.
_UNSAFE_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')

# C0 control range (U+0000-U+001F) plus U+007F (DEL) -- scope doc section 5,
# step 2.
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f]")

# Any run of one or more whitespace characters (spaces, tabs, newlines, and
# the spaces introduced by unsafe-character replacement) -- scope doc
# section 5, step 4.
_WHITESPACE_RUN_PATTERN = re.compile(r"\s+")

# Length cap applied per field (company/role independently), not to the
# final assembled filename -- scope doc section 5, step 7.
_MAX_FIELD_LENGTH = 80

_FALLBACK_COMPANY = "Unknown Company"
_FALLBACK_ROLE = "Unknown Role"


def _sanitize_field(value: str, fallback: str) -> str:
    """Applies the exact 8-step sanitization rule from
    docs/handoffs/NIC-48-product-planner-scope-validation.md section 5 to a
    single field (company or role), independently.

    Order (must not be reordered -- later steps depend on earlier ones):
    1. Trim leading/trailing whitespace.
    2. Strip C0 control characters (U+0000-U+001F) and U+007F (DEL).
    3. Replace filesystem-unsafe characters (< > : " / \\ | ? *) with a
       single space.
    4. Collapse any run of whitespace (incl. tabs/newlines) to a single
       ASCII space.
    5. Trim again (step 4 can reintroduce leading/trailing spaces).
    6. Preserve non-ASCII characters unchanged (no transliteration) --
       this step is a deliberate no-op: nothing above touches non-ASCII
       characters, so accented/non-Latin names pass through untouched.
    7. Truncate to 80 characters (after all of the above, per-field).
    8. If empty/whitespace-only after sanitization, substitute the fixed
       placeholder -- never raise on empty input.
    """
    # Step 1: trim leading/trailing whitespace.
    result = value.strip()

    # Step 2: strip C0 control characters and DEL.
    result = _CONTROL_CHARS_PATTERN.sub("", result)

    # Step 3: replace filesystem-unsafe characters with a single space.
    result = _UNSAFE_CHARS_PATTERN.sub(" ", result)

    # Step 4: collapse any run of whitespace to a single ASCII space.
    result = _WHITESPACE_RUN_PATTERN.sub(" ", result)

    # Step 5: trim again.
    result = result.strip()

    # Step 6: preserve non-ASCII characters -- no-op by construction; no
    # normalization/transliteration is applied above or here.

    # Step 7: truncate to 80 characters (per-field). Implemented exactly as
    # specified -- a hard slice, no additional re-trimming beyond this. In
    # the rare case where the 80-char cut lands exactly on a space (a word
    # boundary), the result may retain a single trailing space; the scope
    # doc's 8-step rule does not call for a post-truncation re-trim, so none
    # is added here (documented as a known edge case, not a spec deviation).
    result = result[:_MAX_FIELD_LENGTH]

    # Step 8: empty/whitespace-only fallback -- never raise on empty input.
    if not result:
        return fallback

    return result


def build_attachment_filename(company: str, role: str, kind: str, ext: str = "pdf") -> str:
    """Builds a sanitized, filesystem-safe attachment filename following the
    `{Company} - {Role} - {Kind}.{ext}` convention (FR-E3, US-7).

    `company` and `role` are independently sanitized per the exact 8-step
    rule in docs/handoffs/NIC-48-product-planner-scope-validation.md
    section 5 (see `_sanitize_field` docstring): control characters and
    filesystem-unsafe characters removed/replaced, whitespace collapsed,
    non-ASCII characters preserved unchanged, each field capped at 80
    characters, empty/whitespace-only input replaced with a fixed
    "Unknown Company" / "Unknown Role" placeholder. This function never
    raises on malformed `company`/`role` input.

    `kind` MUST be one of the closed set {"CV", "Cover Letter"} (exact
    display strings, case-sensitive) -- any other value raises
    `ValueError` rather than silently guessing or normalizing, consistent
    with this codebase's established "fail loudly" style
    (`find_tailored_cv_section`'s behavior when a heading isn't found).

    `ext` defaults to "pdf" (matching NIC-40's confirmed target-format
    decision) and is NOT sanitized -- it is an internally-controlled
    literal value, not external input.

    Returns the assembled filename string, e.g.
    "Acme - Backend Engineer - CV.pdf".
    """
    if kind not in VALID_KINDS:
        raise ValueError(
            f"Invalid kind {kind!r}; must be one of {VALID_KINDS!r} "
            "(exact case, no guessing/normalization)."
        )

    sanitized_company = _sanitize_field(company if company is not None else "", _FALLBACK_COMPANY)
    sanitized_role = _sanitize_field(role if role is not None else "", _FALLBACK_ROLE)

    return f"{sanitized_company} - {sanitized_role} - {kind}.{ext}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print(__doc__)
        print("Usage: python3 scripts/notion_attachment_naming.py <company> <role> <kind> [ext]")
        sys.exit(1)

    company_arg = sys.argv[1]
    role_arg = sys.argv[2]
    kind_arg = sys.argv[3]
    ext_arg = sys.argv[4] if len(sys.argv) > 4 else "pdf"

    print(build_attachment_filename(company_arg, role_arg, kind_arg, ext_arg))
