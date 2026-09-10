#!/usr/bin/env python3
"""NIC-43 Track A: reusable Notion 'children' block-array helper for per-job pages.

Produces the 14-block Notion API `children` array (5 `heading_2` + 5
`callout`/`paragraph` + 4 `divider`) specified in
docs/handoffs/NIC-43-product-planner-scope-validation.md section 7, and
documented in docs/ARCHITECTURE.md ("NIC-43" section).

Any future card-creation code (e.g. NIC-44's conversational Kanban skill, or a
later automation) should import `build_job_page_children()` from this module
and pass its return value as the `children` field of a `POST /v1/pages`
request that ALSO sets `parent.database_id` and `properties` in the SAME
request. Sending `children` in the same call as page creation is what
satisfies AC3 ("applied automatically at card creation, not a manual per-card
formatting step") for API-driven card creation -- see ARCHITECTURE.md's
Track A / Track B distinction for what this does and does not cover (Track B,
a Notion-native UI template for manual "+ New" card creation, is a separate,
non-blocking, manually-configured recommendation, not implemented by this
script).

No Notion SDK dependency: this module returns plain JSON-serializable dicts
matching the Notion API block object shape for API version 2025-09-03. It
performs no network calls itself.

Usage:
    python3 scripts/notion_job_page_blocks.py            # prints JSON array to stdout
    python3 scripts/notion_job_page_blocks.py --count     # prints block count only

    # As a library:
    from notion_job_page_blocks import build_job_page_children
    children = build_job_page_children()
"""
import json
import sys


def _heading_2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text}}]},
    }


def _callout(text: str, emoji: str) -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": text}}],
            "icon": {"emoji": emoji},
            "color": "gray_background",
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def build_job_page_children() -> list:
    """Returns the 14-block `children` array per NIC-43 scope doc section 7.

    Order: Job Details -> Company Research Brief -> Tailored CV ->
    Cover Letter -> Interview Cheat Sheet, each a heading_2 + one
    paragraph/callout placeholder, with a divider between sections
    (no trailing divider after the last section).
    """
    blocks = []

    # 1. Job Details -- freeform, fillable immediately (no upstream dependency).
    blocks.append(_heading_2("\U0001F4CB Job Details"))
    blocks.append(_paragraph("Add job description / posting link here"))
    blocks.append(_divider())

    # 2. Company Research Brief -- placeholder until Phase 3 `company-research` skill ships.
    blocks.append(_heading_2("\U0001F50D Company Research Brief"))
    blocks.append(_callout(
        "Pending \u2014 populated by the `company-research` skill (Phase 3, not yet "
        "built). Will include company summary, recent video, headcount by country, "
        "and recent news within a 12-month window (OQ-14).",
        "\U0001F552",
    ))
    blocks.append(_divider())

    # 3. Tailored CV -- placeholder until Phase 2 `cv-match` PDF output is filed.
    blocks.append(_heading_2("\U0001F4C4 Tailored CV"))
    blocks.append(_callout(
        "Pending \u2014 PDF file will be attached here once `cv-match` output is "
        "filed (Phase 2). Target format: PDF (OQ-13/NIC-40).",
        "\U0001F4CE",
    ))
    blocks.append(_divider())

    # 4. Cover Letter -- placeholder until Phase 2 `write-outreach` PDF output is filed.
    blocks.append(_heading_2("\u2709\uFE0F Cover Letter"))
    blocks.append(_callout(
        "Pending \u2014 PDF file will be attached here once `write-outreach` output "
        "is filed (Phase 2). Target format: PDF (OQ-13/NIC-40).",
        "\U0001F4CE",
    ))
    blocks.append(_divider())

    # 5. Interview Cheat Sheet -- placeholder until job reaches interview stage (Phase 4).
    blocks.append(_heading_2("\U0001F3AF Interview Cheat Sheet"))
    blocks.append(_callout(
        "Pending \u2014 generated once this job reaches an interview stage (Phase 4).",
        "\U0001F552",
    ))

    assert len(blocks) == 14, f"expected 14 blocks, got {len(blocks)}"
    return blocks


if __name__ == "__main__":
    children = build_job_page_children()
    if "--count" in sys.argv:
        print(len(children))
    else:
        print(json.dumps(children, ensure_ascii=False, indent=2))
