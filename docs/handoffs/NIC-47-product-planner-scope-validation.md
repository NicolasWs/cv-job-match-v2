# NIC-47 (P2-T2) — Product Planner Scope Validation

**Ticket:** NIC-47 — "P2-T2 — Native Notion file attachment for cover letter"
**Traces to:** FR-C3, FR-E2, US-6, US-7 (docs/PRD.md)
**Depends on:** P1-T2 / NIC-43 (Per-job Notion page template) — Done; existing `write-outreach` skill (unchanged); P2-T1 / NIC-46 (shared attachment mechanism) — **Done, QA PASS, this same session**
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/implementation performed; this is scope definition only. All investigation below was reading existing files (`scripts/notion_cv_attachment.py`, `scripts/notion_job_page_blocks.py`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/PRD.md`, v1 repo `write-outreach/SKILL.md`) — no Notion API calls were made by Product Planner for this ticket.

---

## 1. Problem

The "✉️ Cover Letter" section on every job's Notion page (block index 9-10 of the 14-block template from `build_job_page_children()`) is currently a placeholder `callout`: *"Pending — PDF file will be attached here once `write-outreach` output is filed (Phase 2)."* `write-outreach` (v1 repo skill) already produces a polished, refined cover letter as an in-session markdown artifact (`applications/<slug>/outreach-v{n}.md`), through a generator→blind-evaluator loop — but that output never leaves the chat session as a file, and it isn't in Notion. Nicolas cannot view or download the cover letter from the job's Notion page today.

## 2. Objective

Attach the final cover letter produced by the existing `write-outreach` skill as a native, viewable/downloadable Notion file on the job's Notion page — reusing NIC-46's already-shipped attachment mechanism (`scripts/notion_cv_attachment.py`) with zero-to-minimal new code, since the mechanism was explicitly designed to be heading-agnostic for exactly this reuse.

**This ticket is about the ATTACHMENT MECHANISM only** — not `write-outreach`'s drafting/refinement logic, and not a PDF-export pipeline inside `write-outreach`. FR-C1/FR-C2 (quality bar, ~250-300 words, refinement loop) describe `write-outreach`'s existing, already-shipped v1 behavior; they are **not new work** for this ticket. They are cited on the ticket only to establish the baseline this attachment step must not regress — verifying that baseline means confirming Builder didn't touch `write-outreach`, not re-testing its drafting quality.

## 3. Investigation: is NIC-46's mechanism reusable as-is?

**Verdict: YES, structurally identical, reusable as-is with no new attachment logic.** Verified by direct code read, not assumed:

- `scripts/notion_job_page_blocks.py` `build_job_page_children()` produces the Cover Letter section exactly like the Tailored CV section: `heading_2("✉️ Cover Letter")` (block index 9) immediately followed by one placeholder `callout` (block index 10), then a `divider` (index 11) before the next section. Same block-type shape as the Tailored CV section (`heading_2` → `callout` → `divider`), just with different heading text and emoji.
- `scripts/notion_cv_attachment.py`'s `attach_final_cv(page_id, pdf_path, filename, heading_text=TAILORED_CV_HEADING)` already takes `heading_text` as a parameter, defaulting to the Tailored CV heading but fully overridable. `find_tailored_cv_section()` (the block-locator it calls) also takes `heading_text` and works purely by string-matching a `heading_2` block's plain text — it has no Tailored-CV-specific logic baked in beyond that default argument value. `REPLACEABLE_BLOCK_TYPES = {"callout", "file", "paragraph"}` is generic, not CV-specific.
- The function's own docstring (lines 289-294) already documents this exact reuse: *"a future ticket (e.g. FR-E2 cover letter attachment) can reuse this function unmodified by passing `heading_text="✉️ Cover Letter"`"* — written by Builder during NIC-46, now the thing this ticket exercises for the first time.
- Confirmed live in `docs/ARCHITECTURE.md`'s NIC-46 "Known limitations" section: *"Cover letter (FR-E2) reuses this exact mechanism but is out of scope for NIC-46 ... not exercised or verified against that heading in this ticket."* NIC-47 is precisely that follow-up.

**Nothing structurally different was found** about the Cover Letter section that would require new upload/replace logic: same block shape, same section-boundary rule (stop at next `divider`/`heading_2`), same file-format target (PDF, OQ-13/NIC-40, confirmed below), same final-version-only requirement (no ticket text or PRD line suggests cover letters should behave differently from CVs on versioning).

**Conclusion: (a) applies.** This ticket is satisfied by *calling* `attach_final_cv(page_id, pdf_path, filename, heading_text="✉️ Cover Letter")` — no new upload/replace/section-locator code is required.

### Naming/wrapper recommendation

I recommend Builder add a **thin wrapper, not a rename of NIC-46's shipped script**:
- Do **not** rename `notion_cv_attachment.py` or its functions — it just shipped, is QA-PASS, and unrelated renames create regression risk on a script another ticket already depends on (violates AGENTS.md "do not make unrelated refactors").
- Add a small new module, e.g. `scripts/notion_cover_letter_attachment.py`, that imports `attach_final_cv` from `notion_cv_attachment.py` and defines a `COVER_LETTER_HEADING = "\u2709\ufe0f Cover Letter"` constant plus a one-line `attach_final_cover_letter(page_id, pdf_path, filename)` convenience wrapper (calls `attach_final_cv(..., heading_text=COVER_LETTER_HEADING)`), with its own CLI entry point mirroring the existing `attach`/`list-section` commands. This keeps the call-site self-documenting (`attach_final_cover_letter` reads better than a bare `heading_text=` string scattered at call sites) while changing zero lines in the already-shipped, QA-passed NIC-46 file.
- This is a documentation/ergonomics call, not a hard requirement — Builder may instead call `attach_final_cv(..., heading_text="✉️ Cover Letter")` directly with no wrapper at all and that would also satisfy every AC below. Either is acceptable; state which was chosen in the handoff.

## 4. Scope — what NIC-47 delivers

**In scope:**
1. Reuse (via direct call or thin wrapper, Builder's choice per §3) of NIC-46's `attach_final_cv()` mechanism, targeting the `"✉️ Cover Letter"` heading, to upload a final cover letter PDF and attach it as a native `file` block on a job's Notion page.
2. Final-version-only retention for the Cover Letter section (same OQ-5 guarantee NIC-46 built — inherited automatically since it's the same function).
3. One-time verification: create exactly **one** test job card (`TEST NIC-47 verification`), attach a small synthetic/dummy PDF to the Cover Letter section, confirm via `GET /v1/blocks/{page_id}/children` that exactly one `file` block sits under the Cover Letter heading and the placeholder callout is gone, fetch the file to confirm it's downloadable, then **archive** the test card immediately after evidence capture.
4. `docs/ARCHITECTURE.md` — new "NIC-47" section (same format as NIC-42/43/46) documenting what was reused vs. added.
5. `docs/PLAN.md` — new NIC-47 entry.

**Out of scope (explicitly, for this ticket):**
- Any change to `write-outreach`'s drafting logic, refinement loop, rubric, or output format — completely untouched. FR-C1/FR-C2 describe existing v1 behavior; verifying them means confirming non-interference, not re-testing quality (see §2).
- Building a PDF-export step inside `write-outreach`. **Confirmed real gap** (verified by reading `write-outreach/SKILL.md` in full, v1 repo): the skill saves drafts as markdown files (`applications/<slug>/outreach-v{n}.md`); there is no PDF-export step anywhere in the skill. This exactly mirrors NIC-46's `cv-match` finding. Per the same authorization pattern NIC-46 used, Builder may use a small synthetic/dummy PDF as the attachment payload to prove the mechanism, and must state this explicitly (not imply it's a real cover letter).
- Any change to `scripts/notion_cv_attachment.py` itself (see §3 naming recommendation — reuse, don't modify, unless Builder finds a genuine defect, which would be a separate finding to flag, not silently fixed here).
- FR-E3 (file naming convention) — same "proposed, not yet confirmed" status as NIC-46 left it; not required to pass this ticket's AC.
- Any card-creation skill/automation, Notion schema changes, Kanban board-view config, n8n automation — untouched.
- Any edit to the v1 repo (`/home/nicow/cv-job-match`) — `write-outreach`'s output is consumed as-is.

## 5. Acceptance criteria (validated, restated as testable)

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | Output structure/quality bar (~250-300 words, native language match, no fabricated claims) matches current `write-outreach` behavior — unchanged, not re-implemented. | Ticket, FR-C1/US-6 | Builder confirms (by file diff / absence of any edit) that `write-outreach/SKILL.md` and its logic in the v1 repo were not touched. No new quality testing required — this is a non-regression confirmation, not new QA scope. |
| AC2 | Refinement-loop behavior unchanged; degrades gracefully to single-pass review outside Claude Code/Cowork. | Ticket, FR-C2 | Same as AC1: confirm no code/skill change was made to the loop logic. Existing v1 `CLAUDE.md`/skill documentation of the fallback behavior is the source of truth and is not modified. |
| AC3 | Final cover letter file is attached to the Notion page as a native file, not just linked to Drive. | Ticket, FR-C3 | Using `attach_final_cv(..., heading_text="✉️ Cover Letter")` (direct or via wrapper), a `file`-type block appears under the job page's "✉️ Cover Letter" heading via the real `file_uploads` 3-step flow. `GET /v1/blocks/{page_id}/children` shows the `file` block with a resolvable Notion-hosted URL (no Drive link involved). |
| AC4 | File is uploaded to Notion, viewable/downloadable from the page. | Ticket, FR-E2 | Fetching the file block's resolvable URL returns the uploaded bytes; content-length/type matches what was uploaded. |
| AC5 | Target file format is PDF (OQ-13, resolved via NIC-40 — not re-litigated). | Ticket note, NIC-40, NIC-46 precedent | `content_type: application/pdf` sent on the `file_uploads` create call; resulting block/file object reflects `.pdf`. |
| AC6 | Only the final version is retained — no accumulation if re-attached (inherits NIC-46's OQ-5 guarantee for this section). | Consistency with NIC-46, PRD FR-E1/E2 parity | Attach once (expect exactly 1 `file` block under Cover Letter); simulate a second "revised letter" attach on the same test card; re-fetch and confirm still exactly 1 `file` block, old one archived not appended. |
| AC7 | The correct job's page (and no other) receives the attachment; the 5 live real production cards are untouched. | Task safety constraint, NIC-46 precedent | Test uses one explicit, hardcoded `page_id` for a dedicated `TEST NIC-47 verification` card (never a name-based lookup). Builder confirms via `GET`/query diff that none of the 5 real cards or NIC-46's own (already-archived) test card were modified. |
| AC8 | Synthetic/dummy PDF is an accepted stand-in for a real `write-outreach` PDF in verification, stated explicitly. | Same authorization pattern as NIC-46 AC5 | Builder's handoff explicitly states the test file was a small synthetic/dummy PDF, not a real `write-outreach` output — no implication of an end-to-end real run unless one was actually performed. |
| AC9 | Test artifact discipline: test card clearly marked, archived immediately after evidence capture. | Task constraints, NIC-43/46 precedent | Test card `Name` contains "TEST NIC-47"; evidence includes creation, verification `GET`, and archive `PATCH {"archived": true}` confirmation in the same handoff. |

## 6. Effort estimate

**XS — approximately 1-1.5 hours.** Smaller than NIC-46 (S, 2-3h) because the attachment mechanism itself requires **zero new logic** — this ticket is a call-site exercise, not new engineering. Breakdown: thin wrapper module or direct call-site decision (~10-15 min), one verification test-card create/attach/inspect/archive cycle with evidence capture (~30-40 min, same shape as NIC-46's but with one section instead of building the whole mechanism), `docs/ARCHITECTURE.md` + `docs/PLAN.md` write-up (~15-20 min).

## 7. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope creep into `write-outreach`'s drafting/refinement logic, since the ticket's AC text cites FR-C1/FR-C2 (quality bar, loop behavior) alongside FR-C3/FR-E2 (attachment). | Medium — could cause Builder to "improve" or re-verify drafting quality, an unrelated refactor forbidden by AGENTS.md. | §2 and AC1/AC2 above explicitly frame these as non-regression confirmations only, not new work. Builder must not open/edit `write-outreach/SKILL.md`. |
| `write-outreach` has no PDF-export step (confirmed fact, mirrors NIC-46's `cv-match` finding) — no way to produce a *real* cover-letter PDF without separate, out-of-scope work. | Medium — same shape as NIC-46's already-accepted risk. | Same authorization already used for NIC-46: synthetic/dummy PDF permitted for verification, stated explicitly (AC8). Recommend this reinforces OQ-A from NIC-46's scope doc (PDF-export step for both `cv-match` and `write-outreach`) as a single combined follow-up ticket rather than two separate ones. |
| Two attachment sections on the same page (Tailored CV, Cover Letter) both use `heading_2`-text matching — if a job's page ever has both headings with identical or near-identical text (unlikely given the emoji+wording difference, but worth noting), the wrong section could be modified. | Low | `find_tailored_cv_section()`'s exact-string match on `heading_text` already disambiguates by construction (`"📄 Tailored CV"` vs `"✉️ Cover Letter"` are not confusable); no new mitigation needed, just noting it was checked. |
| Live workspace has 5 real production cards plus NIC-46's own test card (now archived) — any accidental write during NIC-47 verification would corrupt real data. | Medium | Same discipline as NIC-46: explicit hardcoded `page_id` for a brand-new `TEST NIC-47 verification` card only; AC7 makes the untouched-real-cards check explicit and testable. |
| If Builder chooses the wrapper-module route (§3) and introduces any typo/divergence in the heading constant (e.g. wrong emoji codepoint), the section lookup will fail loudly (`RuntimeError` from `find_tailored_cv_section`) rather than silently mis-targeting — this is a feature of the existing code, not a new risk, but worth confirming Builder tests it. | Low | Existing fail-loud behavior in `notion_cv_attachment.py` already covers this; Builder's verification `GET` before/after naturally catches it. |

## 8. Open questions

- **OQ-A (carried over from NIC-46, reinforced here):** Should a combined follow-up ticket be raised for a PDF-export step covering both `cv-match` and `write-outreach`, since neither v1 skill produces a real PDF file today? Not blocking either ticket, but now confirmed twice.
- **No blockers to starting Builder work.** NIC-46's mechanism, block structure, and OQ-13/PDF decision are all independently re-verified by direct code read for this ticket; no new credential or schema dependency introduced.

## 9. Go/no-go recommendation

**GO.** The dependency this ticket needs (NIC-46's attachment mechanism) is Done/QA-PASS and independently confirmed reusable by direct code read, not assumed. No approval-gate conflict — normal feature work on the project's confirmed architecture, nothing on AGENTS.md's forbidden-operations list. Builder should proceed directly with the smallest-possible increment: a call-site (direct or thin wrapper) into already-shipped code, plus one verification cycle.

---

## HANDOFF TO BUILDER

**Objective:** Attach the final cover letter (from `write-outreach`) as a native Notion `file` block under the "✉️ Cover Letter" section of a job's Notion page, by reusing NIC-46's `attach_final_cv()` mechanism with `heading_text="✉️ Cover Letter"` — no new upload/replace/section-locator logic.

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2`.
- `scripts/notion_cv_attachment.py` — **do not modify.** Reuse `attach_final_cv(page_id, pdf_path, filename, heading_text="✉️ Cover Letter")` directly, or via a new thin wrapper module (recommended: `scripts/notion_cover_letter_attachment.py` with a `COVER_LETTER_HEADING` constant and `attach_final_cover_letter()` convenience function that imports and calls `attach_final_cv`) — your call, document which you picked.
- `scripts/notion_job_page_blocks.py` — Cover Letter section is block index 9-10 (0-indexed) in the 14-block array: `heading_2("✉️ Cover Letter")` immediately followed by the placeholder `callout`.
- Kanban DB: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`.
- `docs/ARCHITECTURE.md` "NIC-46" section — call-shape precedent (3-step file_uploads flow, the `POST {upload_url}` multipart correction, block replace/archive logic) applies unchanged here.
- This document (`docs/handoffs/NIC-47-product-planner-scope-validation.md`) for full rationale.

**Constraints:**
- Do not modify `write-outreach` (v1 repo) or its output logic/format in any way.
- Do not modify `scripts/notion_cv_attachment.py` (NIC-46's shipped, QA-passed file) — reuse only.
- Do not build a PDF-export step for `write-outreach` — use a small synthetic/dummy PDF for verification, stated explicitly in your evidence.
- Do not touch any of the 5 live real job cards, or NIC-46's own (already-archived) test card — create and use your own dedicated `TEST NIC-47 verification` card only, referenced by its own hardcoded `page_id`.
- Test/cleanup discipline (mirrors NIC-46 exactly): create one test card with `Name` containing `TEST NIC-47 verification` (`Company`/`Role`: `TEST`, `Status: selected`, using `build_job_page_children()` for the initial 14-block structure), attach a synthetic PDF to the Cover Letter section via the reused mechanism, run `GET /v1/blocks/{page_id}/children` to confirm exactly one `file` block now exists under the Cover Letter heading and the old callout is gone, fetch the file URL to confirm it's downloadable, simulate one re-attach to prove no accumulation (AC6), THEN immediately `PATCH /v1/pages/{page_id}` `{"archived": true}` and confirm the response. Do not leave the test card live after evidence capture.
- No deployment, no destructive/irreversible operation beyond archiving your own test artifact, no secret exposure, no third-party contact.

**Acceptance criteria:** AC1-AC9 in §5 above.

**Recommended next action:** Builder decides direct-call vs. thin-wrapper (§3), implements accordingly, verifies with the one test card described above, archives it, documents evidence in `docs/ARCHITECTURE.md` (new "NIC-47" section) and `docs/PLAN.md`, and hands off to QA Reviewer with: the exact call made, the block-list GET before/after (showing callout replaced by file block under Cover Letter), the fetched-file confirmation, the no-accumulation re-attach check, and the archive confirmation.
