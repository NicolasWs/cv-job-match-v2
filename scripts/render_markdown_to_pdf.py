#!/usr/bin/env python3
"""NIC-62: markdown -> PDF renderer for real cv-match / write-outreach output.

Per Product Planner scope validation
(docs/handoffs/NIC-62-product-planner-scope-validation.md, section 5), this
module renders a markdown file into a clean, hierarchically-laid-out PDF
using **reportlab directly** (platypus), the same library already backing
the shipped `pdf` skill's `pdf_create.py` CLI (see "Python environment"
note below for exactly which interpreter this repo uses).

It supports two `kind` values:

- `kind="cv"` — renders the ENTIRE input markdown file (e.g.
  `cv-match`'s `applications/<slug>/cv-v{n}.md` output).
- `kind="cover-letter"` — first ISOLATES only the cover-letter section
  from `write-outreach`'s combined markdown output (which bundles cover
  letter + recruiter email + LinkedIn message in one file under headings
  like `## 1. Lettre de motivation` / `## 1. Cover Letter`), then renders
  only that section. The extractor stops at the next `## 2.` heading or a
  `---` divider, and FAILS LOUDLY (raises `CoverLetterBoundaryError`,
  non-zero exit from the CLI) if it cannot confidently find both the start
  and end boundary — it never guesses a truncation point, consistent with
  this repo's established "fail loudly, never guess" style
  (`find_tailored_cv_section`'s behavior in `notion_cv_attachment.py` is
  the precedent cited by the scope doc).

Markdown support (stdlib `re` only, no new third-party dependency beyond
reportlab itself, which is already installed for this repo — see below):

- Headings: `#` (h1/title), `##` (h2/section), `###` (h3/sub-heading).
- Bold inline spans: `**text**` -> reportlab `<b>text</b>` Paragraph markup.
- Italic inline spans: `*text*` -> reportlab `<i>text</i>` Paragraph markup.
- Markdown links: `[text](url)` -> a real clickable reportlab `<link>`.
- Bullet lists: lines starting with `- ` (including multi-line, indented
  wrapped continuations) -> real bulleted `Paragraph` flowables (using
  reportlab's native `bulletText` Paragraph parameter — a genuine bullet
  glyph + hanging indent, not a dash-prefixed run-on blob).
- `---` horizontal rules -> a `Divider` (visual page-break/section rule
  inside the CV; NOT emitted for extracted cover-letter content, since the
  scope doc's layout bar (section 6.2) explicitly forbids source section
  markers -- including `---` dividers -- leaking into the cover-letter PDF).
- A fully-bold single line (e.g. `**Product Owner Senior | ...**` right
  under a CV's name heading, or `**Depuis août 2025**` as a date-range
  line) is detected and rendered in a distinct "emphasis line" style
  (bold, slightly larger than body, extra spacing) rather than as a plain
  body paragraph -- this satisfies the scope doc's "title line beneath
  [the name] in a secondary style, not the same font size as body
  paragraphs" requirement (section 6.1) without inventing any content.
- In `cover-letter` mode, the first paragraph block is treated as the
  salutation and the last paragraph block as the closing/signature line,
  each given extra spacing to visually separate them from the body
  (section 6.2's "Salutation line and closing/signature block visually
  separated from the body paragraphs" requirement) -- a heuristic on
  *position*, not on inventing content that isn't in the source.

No other markdown constructs (tables, nested bullets, images, code
blocks) are handled -- neither `cv-match` nor `write-outreach` currently
emit them (confirmed by the Product Planner's scope doc, section 3, and by
direct inspection of the real NEXTON `cv-v2.md`/`outreach-v2.md` files
used for this ticket's own verification). If a future real file uses them,
this parser will render them as plain paragraph text (visible literal
markdown for anything unsupported) rather than silently corrupting
output -- flagged as a known limitation, not hidden.

Python environment (documented per scope doc section 5, risk table item
"the v2 repo has no requirements.txt/venv of its own"):

    The v2 repo's system Python (`/usr/bin/python3` /
    `/home/nicow/.hermes/hermes-agent/venv/bin/python3`, whichever `python3`
    resolves to on PATH) does NOT have `reportlab` installed -- confirmed by
    direct `import reportlab` failure in this session. The already-shipped
    `pdf` skill's `pdf_create.py` (`~/.hermes/profiles/boss/skills/productivity/pdf/`)
    ALSO failed with the same "Missing dependency" error when actually
    invoked in this session -- i.e. reportlab was NOT already importable
    anywhere reachable on this host at the start of this ticket, despite the
    Product Planner scope doc's assumption that it was (that assumption was
    based on reading the skill's own documentation, not on actually running
    it -- an explicit scope-doc caveat: "no code/implementation performed;
    this is scope definition only" -- so this gap was not visible to that
    read-only investigation).

    Builder's resolution: created a **new, dedicated virtualenv inside this
    v2 repo**, `/home/nicow/cv-job-match-v2/.venv` (via `python3 -m venv .venv`
    then `.venv/bin/python -m ensurepip --upgrade` to obtain `pip`, since the
    system Python has no `pip`/`pip3` binary and PEP 668 blocks a global
    `pip install`), then ` .venv/bin/python -m pip install reportlab` (real
    network install, reportlab 5.0.1, succeeded). This script MUST be run
    with `/home/nicow/cv-job-match-v2/.venv/bin/python3
    scripts/render_markdown_to_pdf.py ...` -- not the bare `python3` on
    PATH, which will raise `ModuleNotFoundError: reportlab` since it is a
    different interpreter with a different site-packages directory. This is
    a one-time, v2-repo-local setup addition (`.venv/`, gitignored, not
    committed) -- no system-wide package install, no change to any other
    script's Python environment, and it does not touch the `pdf` skill's own
    (still-missing) reportlab dependency, which is out of scope for this
    ticket to fix.

Usage as a library:
    from render_markdown_to_pdf import render_markdown_to_pdf

    render_markdown_to_pdf("/path/to/cv-v2.md", kind="cv", out_path="/tmp/cv.pdf")
    render_markdown_to_pdf("/path/to/outreach-v2.md", kind="cover-letter", out_path="/tmp/cl.pdf")

CLI:
    .venv/bin/python3 scripts/render_markdown_to_pdf.py <input.md> --kind cv -o out.pdf
    .venv/bin/python3 scripts/render_markdown_to_pdf.py <input.md> --kind cover-letter -o out.pdf
"""
from __future__ import annotations

import argparse
import os
import re
import sys


class CoverLetterBoundaryError(RuntimeError):
    """Raised when the cover-letter section boundary cannot be confidently
    located in a write-outreach combined markdown file. Never guessed."""


# ---------------------------------------------------------------------------
# Cover-letter section extractor (fail loudly, never guess)
# ---------------------------------------------------------------------------

_COVER_LETTER_START_RE = re.compile(
    r"^##\s+1\.\s*(Lettre de motivation|Cover Letter)\s*$", re.IGNORECASE
)
_SECTION_2_HEADING_RE = re.compile(r"^##\s+2\.", re.IGNORECASE)


def extract_cover_letter_section(markdown_text: str) -> str:
    """Isolates ONLY the cover-letter section from write-outreach's combined
    markdown output (cover letter + recruiter email + LinkedIn message in one
    file). Looks for a `## 1. Lettre de motivation` / `## 1. Cover Letter`
    heading (French/English, case-insensitive) as the start boundary, and
    stops at the next `## 2.` heading OR the first `---` divider after it,
    whichever comes first.

    Raises `CoverLetterBoundaryError` (fail loudly) if either boundary
    cannot be confidently located -- this function never guesses a
    truncation point.
    """
    lines = markdown_text.split("\n")

    start_idx = None
    for i, line in enumerate(lines):
        if _COVER_LETTER_START_RE.match(line.strip()):
            start_idx = i
            break

    if start_idx is None:
        raise CoverLetterBoundaryError(
            "Could not confidently locate the cover-letter section start "
            "heading (expected a line matching '## 1. Lettre de motivation' "
            "or '## 1. Cover Letter', case-insensitive) in the provided "
            "markdown file. Refusing to guess which section is the cover "
            "letter -- this looks like write-outreach output with an "
            "unexpected heading format; escalate rather than extracting "
            "the wrong section."
        )

    end_idx = None
    for j in range(start_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if _SECTION_2_HEADING_RE.match(stripped) or stripped == "---":
            end_idx = j
            break

    if end_idx is None:
        raise CoverLetterBoundaryError(
            "Found the cover-letter section start heading, but could not "
            "confidently locate its end boundary (expected either a "
            "'## 2. ...' heading or a '---' divider somewhere after it). "
            "Refusing to guess a truncation point -- this could mean the "
            "cover-letter section runs to end-of-file with no following "
            "recruiter-email/LinkedIn sections (unexpected for "
            "write-outreach's documented 3-section format), or the "
            "boundary markers are phrased differently than expected."
        )

    section_lines = lines[start_idx + 1 : end_idx]
    section_text = "\n".join(section_lines).strip("\n")

    if not section_text.strip():
        raise CoverLetterBoundaryError(
            "Cover-letter section boundaries were found but the extracted "
            "content between them is empty/whitespace-only. Refusing to "
            "render an empty cover-letter PDF."
        )

    return section_text


# ---------------------------------------------------------------------------
# Markdown block parser (stdlib re only)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_BULLET_RE = re.compile(r"^-\s+(.*)$")
_FULL_BOLD_RE = re.compile(r"^\*\*(.+)\*\*$")


def parse_markdown_blocks(markdown_text: str) -> list[dict]:
    """Parses markdown text into a flat list of block dicts:

    {"type": "heading", "level": 1|2|3, "text": str}
    {"type": "paragraph", "text": str, "full_bold": bool}
    {"type": "bullet_list", "items": [str, ...]}
    {"type": "divider"}

    Paragraphs: consecutive non-blank lines that are not headings/bullets/
    dividers are joined with a single space (markdown "soft wrap" -> one
    logical paragraph), matching the real wrapping style observed in
    cv-match/write-outreach's actual output (e.g. cv-v2.md's summary
    paragraph spans 11 physical lines with no blank-line separators).

    Bullet lists: a line starting with `- ` begins an item; subsequent
    non-blank lines that do NOT start with `- ` and are not headings/
    dividers are treated as wrapped continuations of that same item
    (matches the real indented-continuation style observed in cv-v2.md's
    bullet points, e.g. "- **Label** : detail\\n  continues here").
    """
    lines = markdown_text.split("\n")
    n = len(lines)
    blocks: list[dict] = []
    i = 0

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        if stripped == "":
            i += 1
            continue

        if stripped == "---":
            blocks.append({"type": "divider"})
            i += 1
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append({"type": "heading", "level": level, "text": text})
            i += 1
            continue

        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            items = []
            current = bullet_match.group(1).strip()
            i += 1
            while i < n:
                nxt_raw = lines[i]
                nxt_stripped = nxt_raw.strip()
                if nxt_stripped == "":
                    i += 1
                    break
                if nxt_stripped == "---" or _HEADING_RE.match(nxt_stripped):
                    break
                nxt_bullet = _BULLET_RE.match(nxt_stripped)
                if nxt_bullet:
                    items.append(current)
                    current = nxt_bullet.group(1).strip()
                    i += 1
                    continue
                # wrapped continuation of the current bullet item
                current += " " + nxt_stripped
                i += 1
            items.append(current)
            blocks.append({"type": "bullet_list", "items": items})
            continue

        # paragraph: merge consecutive non-blank, non-special lines
        para_lines = [stripped]
        i += 1
        while i < n:
            nxt_raw = lines[i]
            nxt_stripped = nxt_raw.strip()
            if (
                nxt_stripped == ""
                or nxt_stripped == "---"
                or _HEADING_RE.match(nxt_stripped)
                or _BULLET_RE.match(nxt_stripped)
            ):
                break
            para_lines.append(nxt_stripped)
            i += 1
        text = " ".join(para_lines)
        full_bold = bool(_FULL_BOLD_RE.match(text)) and text.count("**") == 2
        blocks.append({"type": "paragraph", "text": text, "full_bold": full_bold})

    return blocks


# ---------------------------------------------------------------------------
# Inline markdown -> reportlab Paragraph XML-subset markup
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")


# Characters observed in real cv-match/write-outreach output (confirmed by
# a full character-inventory scan of the real NEXTON cv-v2.md/outreach-v2.md
# files used for this ticket's own verification) that the registered
# NotoSans-Regular.ttf's cmap does NOT cover (confirmed via a direct
# fontTools cmap check against this exact font file on this host) -- without
# substitution these render as a missing-glyph placeholder (NUL/empty box),
# which is worse for the "no visible raw markdown / clean readable output"
# quality bar than a plain-ASCII equivalent. Substituted to a lossless,
# meaning-preserving ASCII form (documented limitation, not silent data
# loss): "→" (U+2192 RIGHTWARDS ARROW) -> "->", "≤" (U+2264 LESS-THAN OR
# EQUAL TO) -> "<=". No other character substitution is performed --
# accented Latin characters, em/en dashes, the euro sign, and the middle
# dot are all natively covered by NotoSans-Regular's cmap (confirmed) and
# are rendered as-is.
_GLYPH_FALLBACK_SUBSTITUTIONS = {
    "\u2192": "->",  # RIGHTWARDS ARROW
    "\u2264": "<=",  # LESS-THAN OR EQUAL TO
}


def _apply_glyph_fallbacks(text: str) -> str:
    for original, replacement in _GLYPH_FALLBACK_SUBSTITUTIONS.items():
        text = text.replace(original, replacement)
    return text


def _escape_xml(text: str) -> str:
    text = _apply_glyph_fallbacks(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline_markdown_to_reportlab(text: str) -> str:
    """Converts a single line/paragraph of markdown inline syntax into
    reportlab's Paragraph XML-subset markup. Order matters: escape XML
    entities first (so literal `&`/`<`/`>` in real content, e.g. company
    names, don't break the markup), then markdown links, then bold, then
    italic (bold consumes `**` pairs first so a leftover single `*` isn't
    mis-parsed as italic).
    """
    escaped = _escape_xml(text)

    def _link_sub(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        return f'<link href="{url}" color="#1a5276"><u>{label}</u></link>'

    with_links = _MD_LINK_RE.sub(_link_sub, escaped)
    with_bold = _BOLD_RE.sub(r"<b>\1</b>", with_links)
    with_italic = _ITALIC_RE.sub(r"<i>\1</i>", with_bold)
    return with_italic


def strip_full_bold_wrapper(text: str) -> str:
    """For a paragraph block flagged `full_bold=True`, strips the outer
    `**...**` wrapper before inline conversion (the whole line already gets
    a dedicated bold "emphasis line" style, so we don't want doubled
    `<b><b>...</b></b>` markup)."""
    m = _FULL_BOLD_RE.match(text)
    return m.group(1) if m else text


# ---------------------------------------------------------------------------
# PDF rendering (reportlab platypus, direct)
# ---------------------------------------------------------------------------

_NOTO_SANS_CANDIDATES = {
    "NotoSans": "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "NotoSans-Bold": "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    "NotoSans-Italic": "/usr/share/fonts/noto/NotoSans-Italic.ttf",
    "NotoSans-BoldItalic": "/usr/share/fonts/noto/NotoSans-BoldItalic.ttf",
}

_UNICODE_FONT_REGISTERED = False


def _register_unicode_font() -> str:
    """Registers the system-installed Noto Sans TTF family with reportlab
    (if present) and returns the base font family name to use for body
    text. Falls back to reportlab's built-in Helvetica (WinAnsi-only) if
    Noto Sans isn't found on this host, which would show `(cid:127)`-style
    glyph-not-found placeholders for characters outside WinAnsi (e.g. the
    bullet `→` arrow, some accented forms). The real NEXTON CV/cover
    letter content is French with standard Latin-1 accents (fully covered
    by Helvetica/WinAnsi) plus a small number of typographic characters
    (`→`, em/en dashes, curly quotes, bullet glyphs) that Helvetica's base
    14 fonts do NOT cover -- registering Noto Sans (already installed
    system-wide on this host, confirmed via `fc-list`/direct file check,
    not a new dependency) fixes this without inventing/adding content.
    """
    global _UNICODE_FONT_REGISTERED
    if _UNICODE_FONT_REGISTERED:
        return "NotoSans"

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    if not all(os.path.exists(p) for p in _NOTO_SANS_CANDIDATES.values()):
        return "Helvetica"

    for name, path in _NOTO_SANS_CANDIDATES.items():
        pdfmetrics.registerFont(TTFont(name, path))
    registerFontFamily(
        "NotoSans",
        normal="NotoSans",
        bold="NotoSans-Bold",
        italic="NotoSans-Italic",
        boldItalic="NotoSans-BoldItalic",
    )
    _UNICODE_FONT_REGISTERED = True
    return "NotoSans"


def _build_styles():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base_font = _register_unicode_font()
    bold_font = f"{base_font}-Bold" if base_font == "NotoSans" else "Helvetica-Bold"

    base = getSampleStyleSheet()
    styles = {}

    styles["h1"] = ParagraphStyle(
        "NIC62Heading1",
        parent=base["Normal"],
        fontName=bold_font,
        fontSize=22,
        leading=26,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1a1a"),
        alignment=TA_LEFT,
    )
    styles["subtitle"] = ParagraphStyle(
        "NIC62Subtitle",
        parent=base["Normal"],
        fontName=bold_font,
        fontSize=12.5,
        leading=16,
        spaceAfter=10,
        textColor=colors.HexColor("#34495e"),
    )
    styles["h2"] = ParagraphStyle(
        "NIC62Heading2",
        parent=base["Normal"],
        fontName=bold_font,
        fontSize=15,
        leading=18,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#1a5276"),
        borderWidth=0,
    )
    styles["h3"] = ParagraphStyle(
        "NIC62Heading3",
        parent=base["Normal"],
        fontName=bold_font,
        fontSize=11.5,
        leading=14,
        spaceBefore=10,
        spaceAfter=3,
        textColor=colors.HexColor("#212f3d"),
    )
    styles["body"] = ParagraphStyle(
        "NIC62Body",
        parent=base["Normal"],
        fontName=base_font,
        fontSize=10,
        leading=13.5,
        spaceAfter=7,
        alignment=TA_LEFT,
    )
    styles["emphasis_line"] = ParagraphStyle(
        "NIC62EmphasisLine",
        parent=base["Normal"],
        fontName=bold_font,
        fontSize=10,
        leading=13,
        spaceBefore=1,
        spaceAfter=6,
        textColor=colors.HexColor("#34495e"),
    )
    styles["bullet"] = ParagraphStyle(
        "NIC62Bullet",
        parent=base["Normal"],
        fontName=base_font,
        fontSize=10,
        leading=13.5,
        leftIndent=16,
        bulletIndent=4,
        spaceAfter=4,
    )
    styles["salutation"] = ParagraphStyle(
        "NIC62Salutation",
        parent=base["Normal"],
        fontName=base_font,
        fontSize=10.5,
        leading=14,
        spaceBefore=4,
        spaceAfter=14,
    )
    styles["closing"] = ParagraphStyle(
        "NIC62Closing",
        parent=base["Normal"],
        fontName=base_font,
        fontSize=10.5,
        leading=14,
        spaceBefore=16,
        spaceAfter=4,
    )
    return styles


def _blocks_to_flowables(blocks: list[dict], styles: dict, is_cover_letter: bool = False):
    from reportlab.platypus import Paragraph, Spacer, HRFlowable

    flowables = []

    # Positional heuristics for cover-letter salutation/closing (section
    # 6.2 of the scope doc): first/last *paragraph* blocks get distinct
    # spacing styles. Computed up front since it depends on full-list
    # position, not on a single block in isolation.
    paragraph_indices = [idx for idx, b in enumerate(blocks) if b["type"] == "paragraph"]
    first_para_idx = paragraph_indices[0] if (is_cover_letter and paragraph_indices) else None
    last_para_idx = paragraph_indices[-1] if (is_cover_letter and paragraph_indices) else None

    prev_type = None
    for idx, block in enumerate(blocks):
        btype = block["type"]

        if btype == "heading":
            level = block["level"]
            style_key = {1: "h1", 2: "h2", 3: "h3"}.get(level, "h3")
            text = inline_markdown_to_reportlab(block["text"])
            flowables.append(Paragraph(text, styles[style_key]))

        elif btype == "paragraph":
            if block.get("full_bold"):
                inner = strip_full_bold_wrapper(block["text"])
                text = inline_markdown_to_reportlab(inner)
                flowables.append(Paragraph(text, styles["emphasis_line"]))
            else:
                text = inline_markdown_to_reportlab(block["text"])
                if idx == first_para_idx:
                    style = styles["salutation"]
                elif idx == last_para_idx:
                    style = styles["closing"]
                else:
                    style = styles["body"]
                flowables.append(Paragraph(text, style))

        elif btype == "bullet_list":
            for item in block["items"]:
                text = inline_markdown_to_reportlab(item)
                flowables.append(Paragraph(text, styles["bullet"], bulletText="\u2022"))

        elif btype == "divider":
            # Cover-letter mode never reaches here in practice (the
            # extractor stops at the first '---'), but guard anyway per
            # the layout bar: no source section markers may leak into the
            # cover-letter PDF.
            if not is_cover_letter:
                flowables.append(Spacer(1, 6))
                flowables.append(HRFlowable(width="100%", color="#cccccc", thickness=0.6))
                flowables.append(Spacer(1, 6))

        prev_type = btype

    return flowables


def render_blocks_to_pdf(blocks: list[dict], out_path: str, title: str, is_cover_letter: bool = False) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate

    styles = _build_styles()
    flowables = _blocks_to_flowables(blocks, styles, is_cover_letter=is_cover_letter)

    if not flowables:
        raise RuntimeError(f"No renderable content produced for {out_path!r} -- refusing to write an empty PDF.")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=title,
        author="cv-job-match v2 (NIC-62 renderer)",
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.drawRightString(A4[0] - 2.0 * cm, 1.2 * cm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(flowables, onFirstPage=_footer, onLaterPages=_footer)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

VALID_KINDS = ("cv", "cover-letter")


def render_markdown_to_pdf(markdown_path: str, kind: str, out_path: str) -> str:
    """Renders `markdown_path` to a PDF at `out_path`.

    `kind="cv"` renders the whole file. `kind="cover-letter"` first extracts
    only the cover-letter section (raising `CoverLetterBoundaryError` if the
    boundary can't be confidently found) then renders only that section.

    Returns `out_path` on success.
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind {kind!r}; must be one of {VALID_KINDS!r}")

    with open(markdown_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    if kind == "cv":
        blocks = parse_markdown_blocks(raw_text)
        title = os.path.splitext(os.path.basename(markdown_path))[0] or "Tailored CV"
        render_blocks_to_pdf(blocks, out_path, title=title, is_cover_letter=False)
    else:
        section_text = extract_cover_letter_section(raw_text)
        blocks = parse_markdown_blocks(section_text)
        title = "Cover Letter"
        render_blocks_to_pdf(blocks, out_path, title=title, is_cover_letter=True)

    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description="Render real cv-match/write-outreach markdown output into a clean PDF (NIC-62)."
    )
    parser.add_argument("markdown_path", help="Path to the input markdown file")
    parser.add_argument(
        "--kind", required=True, choices=VALID_KINDS,
        help="'cv' renders the whole file; 'cover-letter' extracts and renders only the cover-letter section",
    )
    parser.add_argument("-o", "--out", required=True, help="Output PDF path")
    args = parser.parse_args()

    try:
        result = render_markdown_to_pdf(args.markdown_path, args.kind, args.out)
    except CoverLetterBoundaryError as e:
        print(f"FAILED (cover-letter boundary detection, refusing to guess): {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: wrote {result}")


if __name__ == "__main__":
    _main()
