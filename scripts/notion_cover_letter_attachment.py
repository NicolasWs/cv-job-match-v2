#!/usr/bin/env python3
"""NIC-47: thin wrapper reusing NIC-46's shared Notion attachment mechanism
for the "Cover Letter" section of a job's Notion page.

Per Product Planner scope validation
(docs/handoffs/NIC-47-product-planner-scope-validation.md, section 3),
`scripts/notion_cv_attachment.py`'s `attach_final_cv()` is heading-agnostic
and already accepts a `heading_text` override -- no new upload/replace/
section-locator logic is needed for cover letters. This module changes
ZERO lines in that already-shipped, QA-passed file. It only:

1. Defines `COVER_LETTER_HEADING`, matching the exact heading text produced
   by `scripts/notion_job_page_blocks.py`'s `build_job_page_children()`
   (block index 9, 0-indexed, in the 14-block array): "\u2709\ufe0f Cover Letter".
2. Provides `attach_final_cover_letter(page_id, pdf_path, filename)`, a
   one-line convenience function that imports and calls
   `attach_final_cv(..., heading_text=COVER_LETTER_HEADING)` from
   `notion_cv_attachment.py`.
3. Mirrors the existing `attach`/`list-section` CLI commands for cover
   letters specifically, so call-sites read `attach_final_cover_letter(...)`
   rather than a bare `heading_text="..."` string literal scattered around
   the codebase.

No new Notion API call shapes, no new HTTP logic, no Notion SDK dependency
-- this module is a pure re-export/convenience layer on top of
`notion_cv_attachment.py`.

Usage as a library:
    from notion_cover_letter_attachment import attach_final_cover_letter

    result = attach_final_cover_letter(
        page_id="...",
        pdf_path="/path/to/cover-letter.pdf",
        filename="Acme - Backend Engineer - Cover Letter.pdf",
    )

CLI (manual/scripted verification only; caller must supply an explicit,
already-known page_id -- never a name-matched lookup):
    python3 scripts/notion_cover_letter_attachment.py attach <page_id> <pdf_path> [filename]
    python3 scripts/notion_cover_letter_attachment.py list-section <page_id>
"""
import json
import sys

from notion_cv_attachment import attach_final_cv, find_tailored_cv_section

# Must exactly match the heading text produced by
# scripts/notion_job_page_blocks.py's build_job_page_children() (block index
# 9, 0-indexed, in the 14-block array).
COVER_LETTER_HEADING = "\u2709\ufe0f Cover Letter"


def attach_final_cover_letter(page_id: str, pdf_path: str, filename: str) -> dict:
    """Convenience wrapper: calls NIC-46's `attach_final_cv()` unmodified,
    targeting the Cover Letter section instead of the default Tailored CV
    section. No new logic beyond supplying `heading_text`.
    """
    return attach_final_cv(page_id, pdf_path, filename, heading_text=COVER_LETTER_HEADING)


def find_cover_letter_section(page_id: str) -> dict:
    """Convenience wrapper around `find_tailored_cv_section()` (which is
    heading-text-driven despite its name) for the Cover Letter heading."""
    return find_tailored_cv_section(page_id, heading_text=COVER_LETTER_HEADING)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    page_id = sys.argv[2]

    if cmd == "attach":
        pdf_path = sys.argv[3]
        filename = sys.argv[4] if len(sys.argv) > 4 else pdf_path.split("/")[-1]
        result = attach_final_cover_letter(page_id, pdf_path, filename)
        print(json.dumps(result, indent=2, default=str))
    elif cmd == "list-section":
        section = find_cover_letter_section(page_id)
        print(json.dumps({
            "heading_block_id": section["heading_block_id"],
            "section_block_ids": section["section_block_ids"],
            "replaceable_block_ids": section["replaceable_block_ids"],
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
