# NIC-46 (P2-T1) — Product Planner Scope Validation

**Ticket:** NIC-46 — "P2-T1 — Native Notion file attachment for tailored CV"
**Traces to:** FR-E1, US-7 (docs/PRD.md)
**Depends on:** P1-T2 / NIC-43 (Per-job Notion page template) — **Done**; existing `cv-match` skill output (unchanged)
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/implementation performed; this is scope definition only. All Notion API calls made below were read-only investigation (GET/search/query) plus one harmless, self-expiring `file_uploads` placeholder probe — no page, card, or block was created, modified, or deleted.

---

## 1. Problem

Phase 1 (NIC-42, NIC-43) built the structural home for a job's tailored CV — a "📄 Tailored CV" section on every job's Notion page, currently rendered as a placeholder `callout` block reading "Pending — PDF file will be attached here once `cv-match` output is filed (Phase 2)." Nothing fills that placeholder yet. `cv-match` (v1 repo skill) already produces a tailored CV as an in-session markdown/text artifact, refined through a generator→evaluator loop, but that output never leaves the chat session — it isn't a file, and it isn't in Notion. Nicolas cannot view or download the tailored CV from the job's Notion page today; the single-source-of-truth promise of the v2 architecture is unmet for this section.

## 2. Objective

Define exactly how the final tailored CV becomes a **native Notion file** attached to (viewable/downloadable from) the correct job's Notion page, using the real Notion file-upload API, with only the final version retained (no refinement-loop drafts persisted), so Builder can implement the smallest correct increment without further scope negotiation.

**This ticket is about the ATTACHMENT MECHANISM only** — not about changing `cv-match`'s own analysis/refinement logic, and not about building a PDF-export pipeline inside `cv-match`. `cv-match`'s output format and process are explicitly unchanged (ticket's own "Depends on" line, and PRD's FR-E1 note: "existing `cv-match` skill output (unchanged)").

## 3. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` — handoff contract, Linear lifecycle, approval gates.
- `docs/PRD.md` — FR-E1/E2/E3 (line 150-155), US-7 (line 267), OQ-5 (line 229, "Final version only"), OQ-13 (line 240, listed as open in the PRD table itself).
- `docs/PLAN.md` — NIC-42 (Done, schema), NIC-43 (Done, block helper + Tailored CV placeholder), NIC-45 (Notion sole tracker of record, v2 policy).
- `docs/ARCHITECTURE.md` — NIC-42 (Kanban schema/IDs), NIC-43 (block schema; the Tailored CV callout text explicitly says "Target format: PDF (OQ-13/NIC-40)").
- `scripts/notion_job_page_blocks.py` — read in full. `build_job_page_children()` produces the 14-block array; block #3 is `heading_2("📄 Tailored CV")` + `callout("...Target format: PDF (OQ-13/NIC-40).", "📎")`.
- `docs/handoffs/NIC-43-product-planner-scope-validation.md` — prior Product Planner explicitly flagged (§9 risk table): "`file` blocks cannot exist 'empty' in the Notion API — CV/Cover Letter placeholders must use `callout`/`paragraph` blocks now, then be **replaced or appended** by a real `file` block once Phase 2 ships." This is load-bearing for NIC-46's design (§6 below).
- `docs/handoffs/NIC-44-product-planner-scope-validation.md` — confirms no card-creation skill exists yet; cards today are created manually.
- `notion` skill (`~/.hermes/profiles/boss/skills/productivity/notion/SKILL.md`) — file-upload 3-step flow (`POST /v1/file_uploads` → `PUT` bytes to `upload_url` → reference `file_upload_id` in a block), and `ntn files create` one-liner shortcut.
- `linear` skill — GraphQL query/mutation patterns.
- v1 repo `/home/nicow/cv-job-match/.claude/skills/cv-match/SKILL.md` — confirmed `cv-match` produces a tailored CV as in-session structured text/markdown (Match Score, edit list, refined draft) with **no PDF-export step** anywhere in the skill file. This is a **fact**, not an assumption: the skill's Phase 1/2 description covers parse → match → tailor → refine, and stops there.

### Live investigation performed (read-only + one harmless probe)

- `NOTION_API_KEY` is **set and working**: verified via a real `POST /v1/search` call (returned the "Job Search Kanban" data source) and a real `POST /v1/data_sources/{id}/query` call (returned 5 live cards). Credential is **not** a blocker.
- `POST /v1/file_uploads` capability check: sent a minimal `{"filename": "test-permission-check.txt"}` body and got **`200 OK`**, confirming the integration has file-upload permission on this workspace. This created one harmless, unreferenced `file_upload` placeholder object (never linked to any page/block); Notion auto-expires unused file uploads, and since it holds no bytes and is attached nowhere, no cleanup action is required or possible via a page/card archive. Flagging for full transparency, per this repo's no-fabrication discipline.
- Queried the live Kanban database (`data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`): **5 real, non-archived cards already exist** (e.g. "Upslide", "InvestHub", "Implementation Manager - Strategic Accounts"), created outside of any factory ticket (not via the NIC-43 block helper — they don't have the 14-block structure; one card has 22 freeform blocks that look like manually-pasted real `cv-match` output). **This is new information not reflected in PLAN.md's "zero cards" framing (which was accurate at NIC-42/43 time but is now stale).** Practical implication for Builder: the live workspace now contains real production data, not just an empty schema — Builder's test/verification card must be unmistakably marked as a test (per the ticket's own constraint) and must not touch any of these 5 real cards.
- Checked `NIC-40` in Linear directly (id resolved via `issues(filter: number eq 40)`): status **Done**, with a closing comment (in French, 2026-09-10) confirming: *"Décision validée par Nico : format PDF retenu comme format cible pour les pièces jointes natives Notion (CV taillé sur mesure et lettre de motivation)... S'applique à FR-C3, FR-E1, FR-E2, FR-E3."* This independently confirms the task context's claim — **PDF is a genuinely resolved decision**, not just something asserted in ARCHITECTURE.md's block-helper comments. **No contradiction found.**

## 4. OQ-13 status — resolved to PDF, ticket text is stale

The NIC-46 ticket's own description still lists file format as an open question ("not yet decided"). Investigation confirms this line is **stale**: OQ-13 was closed by NIC-40 (Done, Linear-verified above) and is independently echoed in `docs/ARCHITECTURE.md`'s NIC-43 section and in the literal placeholder text already sitting in `scripts/notion_job_page_blocks.py` line 98 ("Target format: PDF (OQ-13/NIC-40)"). **Decision: treat PDF as the confirmed target format for this ticket.** No contradiction was found across PRD, ARCHITECTURE, PLAN, the shipped code, or Linear itself — all four sources agree. Builder should not re-litigate this; if a future ticket wants Markdown/DOCX as an *additional* format, that is new scope, not a NIC-46 concern.

## 5. Scope — what NIC-46 delivers

**In scope:**
1. A mechanism that takes a **final tailored CV file** (already in PDF form) and uploads it to Notion using the real 3-step `file_uploads` flow (create → PUT bytes → reference), producing a `file` block referencing that upload.
2. A mechanism to **locate the correct job's page** and its Tailored CV section (the `heading_2("📄 Tailored CV")` + placeholder `callout` produced by `build_job_page_children()`), and either replace the callout with the new `file` block or append the `file` block immediately after the callout and remove/archive the stale callout — so the section shows exactly one thing: the real file, not the file *and* the leftover "Pending" text.
3. **Final-version-only retention (OQ-5):** if the CV for a job is revised and the ticket/skill is re-run, the mechanism must remove the previously attached file block (or replace it in place) rather than appending a second file block — the section must never accumulate multiple CV versions.
4. One-time verification: Builder creates exactly **one** test job card (clearly named, e.g. `TEST NIC-46 verification`), attaches a small **synthetic/dummy PDF** (not a real cv-match run) to prove the attachment mechanism end-to-end, confirms via `GET /v1/blocks/{page_id}/children` that a `file` block is present and the file is fetchable, then **archives** the test card immediately after evidence capture.
5. Documentation of the call shapes (file_uploads 3-step flow, block replace/append logic) in `docs/ARCHITECTURE.md` (new "NIC-46" section, same format as NIC-42/NIC-43).

**Out of scope (explicitly, for this ticket):**
- Any change to `cv-match`'s analysis, refinement loop, Match Score, or edit-list logic — completely untouched (per ticket's own "Depends on" line).
- Building a PDF-export step inside `cv-match` (or anywhere) that turns its current markdown/text output into an actual PDF. **This is a confirmed real gap** (verified by reading `cv-match/SKILL.md` — no export step exists), not a hypothetical. Per this ticket's constraints, Builder is authorized to use a small synthetic/dummy PDF as the attachment payload to prove the mechanism; this must be stated as a known limitation in Builder's evidence, not hidden or implied to be a real CV.
- FR-E2 (cover letter attachment) — same mechanism will very likely be reusable, but this ticket's AC and verification are scoped to the **tailored CV only**, per the ticket title and description. Flagged as a natural, low-effort follow-up (§9 below), not silently bundled in.
- FR-E3 (file naming convention, `{Company} - {Role} - CV.pdf`) — PRD marks this as "proposed, not yet confirmed." Recommend Builder adopt it as a reasonable default filename for the uploaded file (low risk, matches PRD's stated intent), but this ticket's AC does not require a specific naming scheme to pass; note in Builder's evidence what naming convention was actually used.
- Any card-creation skill or automation — still doesn't exist (confirmed, NIC-44 scope), not part of this ticket.
- Notion database schema changes, Kanban board-view config, n8n automation — untouched.
- Any edit to the v1 repo (`/home/nicow/cv-job-match`) — `cv-match`'s output is consumed as-is; the CV file itself is expected to arrive as a file on disk (however produced) and is not this ticket's concern to generate.

## 6. Key design point: replace-or-append at the placeholder callout, not a page property

`build_job_page_children()` (NIC-43) placed the Tailored CV placeholder as a `callout` block because the Notion API cannot create an "empty" `file` block — this was flagged as a known limitation by the prior Product Planner in the NIC-43 scope doc and is now exactly the seam NIC-46 must close. Two implementation options exist; Builder should pick and document one:

- **Option A (recommended): block-level `file` object.** `PATCH /v1/blocks/{page_id}/children` (or a targeted block operation) to append a `file` block referencing the uploaded `file_upload_id`, then delete/archive the old placeholder `callout` block (`DELETE /v1/blocks/{block_id}` or equivalent archive) so exactly one artifact remains under the "📄 Tailored CV" heading. This matches the section-based page layout NIC-43 established and requires no schema change.
- **Option B: page-level file property.** Add a new `Files & media` property to the NIC-42 database schema and attach the file there instead of in page content. **Not recommended for this ticket** — it's a schema change (out of NIC-42's closed scope, needs its own decision) and breaks the section-based reading order NIC-43 built. Flag as an alternative only if Option A proves technically blocked.

Whichever option is used, "final version only" (OQ-5) means: **exactly one file reference under the Tailored CV section per job, at all times** — never a growing list.

## 7. Acceptance criteria (validated, restated as testable)

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | The final tailored CV file is uploaded to Notion and is viewable/downloadable from the job's Notion page. | Ticket, FR-E1 | Using the real `file_uploads` 3-step flow (`POST /v1/file_uploads` → `PUT` bytes to the returned `upload_url` → block referencing `file_upload_id`), a `file` block appears under the job page's "📄 Tailored CV" heading. `GET /v1/blocks/{page_id}/children` shows a `file`-type block with a resolvable Notion-hosted URL; fetching that URL returns the uploaded bytes (verify content-length/type matches what was uploaded). |
| AC2 | Only the final version is retained in Notion — refinement-loop intermediate drafts are never uploaded, and re-attaching a revised CV does not leave stale/duplicate files behind. | Ticket, OQ-5 | (a) Intermediate-draft check: nothing in the mechanism ever calls `file_uploads` for anything but the CV the skill has already finished refining — verified by inspecting Builder's implementation, no drafts uploaded during a simulated refinement loop. (b) No-accumulation check: attach a file once, capture the block list (expect exactly 1 `file` block in that section); simulate a second "revised CV" attach on the same test card; re-fetch the block list and confirm still exactly 1 `file` block (old one removed/replaced, not appended alongside). |
| AC3 | Target file format is PDF (OQ-13, confirmed resolved — see §4). | Task context, NIC-40, ARCHITECTURE.md | The uploaded test file has `content_type: application/pdf` in the `file_uploads` create call, and the resulting Notion `file` block's mime type / filename extension reflects `.pdf`. |
| AC4 | The correct job's page (and no other) receives the attachment. | Implied by FR-E1 (per-job), consistent with NIC-44's ambiguity-safety precedent | Test uses an explicit, known `page_id` for the one test card created for this ticket (not a name-based lookup that could misfire) — Builder states which `page_id` it targeted and confirms via `GET` that no other existing card's page (the 5 live real cards found during investigation, or any other test card) was modified. |
| AC5 | `cv-match`'s own output/logic is unchanged; a synthetic/dummy PDF is an accepted stand-in for a real cv-match PDF in this ticket's verification, and this is stated explicitly, not hidden. | Ticket constraints, this doc §5 | Builder's handoff explicitly states the test file was a small synthetic/dummy PDF (e.g., "1-page placeholder PDF generated for mechanism testing, not a real cv-match output") — no claim that a real end-to-end cv-match→PDF→Notion run was performed unless Builder actually did generate a real one. |
| AC6 | Test artifact discipline: any card/data created for verification is clearly marked as a test and archived immediately after evidence capture. | Task constraints (mirrors NIC-43 precedent) | Test card's `Name` property contains "TEST NIC-46" (or equivalent), and Builder's evidence includes both the creation response/verification GET **and** the archive `PATCH {"archived": true}` confirmation, in the same handoff — mirroring NIC-43's exact pattern (`docs/handoffs/NIC-43...`, `ARCHITECTURE.md` NIC-43 section). |

## 8. Effort estimate

**S — approximately 2–3 hours.** Breakdown: file-upload 3-step flow implementation/scripting (~45 min — the notion skill already documents the exact call shapes, no discovery needed), block replace/append-at-placeholder logic (~45 min — the seam is already identified and flagged by NIC-43's own risk table), one verification test-card create/attach/inspect/archive cycle with evidence capture (~30-45 min), `docs/ARCHITECTURE.md` write-up (~20-30 min). Smaller than NIC-43 (S/M, 3-4h) because the block schema, database IDs, and placeholder locations are all already established — this ticket fills an already-designed seam rather than designing new structure.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Notion file size limits: free workspaces are capped at 5 MB **single-part only** (multi-part uploads are refused outright); paid workspaces support multi-part up to 5 GB. A real tailored CV PDF is typically well under 1 MB, so this is low risk in practice, but Builder should confirm the workspace's plan/limit (`GET /v1/users/me` or equivalent) before assuming multi-part is available if a larger file is ever used. | Low (test files are tiny) / Medium if this pattern is later reused for larger attachments | State the observed limit in Builder's evidence; use single-part upload for the small test PDF, which is well within any tier's limit. |
| `cv-match` has no real PDF-export step today (confirmed fact, §5) — there is currently no way to produce a *real* tailored-CV PDF as an input to this mechanism without separate, out-of-scope work. | Medium — could tempt Builder to either fabricate a "real" CV PDF's content or silently skip stating this gap. | Ticket constraints already authorize a synthetic/dummy PDF for verification; AC5 requires this to be stated explicitly. Recommend a follow-up ticket (or PRD note) for "PDF export step for cv-match/write-outreach output" as a prerequisite for a true end-to-end Phase 2 flow — flagged as OQ-A below. |
| Live workspace now has 5 real, non-test job cards (new finding, not in PLAN.md) — any accidental write to those during Builder/QA verification would corrupt real pipeline data, which AGENTS.md forbids without human approval. | Medium | Builder must use an explicit, hardcoded `page_id` for its own newly-created test card only — never a search/filter that could match a real card by name coincidence. AC4 makes this an explicit testable check. |
| Replacing vs. appending the placeholder `callout` block: if Builder appends the `file` block but forgets to remove the old callout, the page will show both "Pending..." text and the real file, which is confusing and could look like AC1 failing at a glance even though the file itself works. | Low-Medium (cosmetic but could cause a false QA fail or false Nicolas impression that something's broken) | AC1's testable check should include visually/structurally confirming the callout is gone or updated, not just that a file block exists somewhere on the page. |
| Two different attachment locations are architecturally possible (block-level `file` object under the section vs. a page-level "Files & media" property) — picking the wrong one creates rework for FR-E2 (cover letter, same pattern expected) later. | Low | §6 makes an explicit recommendation (Option A, block-level, matching NIC-43's established page structure) so Builder doesn't have to re-decide this from scratch. |

## 10. Open questions

- **OQ-A (not blocking, follow-up):** Should a new ticket be raised for a `cv-match` (and `write-outreach`) PDF-export step, since neither skill currently produces a real PDF file? This is a prerequisite for a *true* end-to-end Phase 2 flow (real CV → real file → Notion) but is explicitly out of scope for NIC-46 per the ticket's own constraints. Recommend flagging to Nicolas after this ticket ships.
- **OQ-B (not blocking):** Should FR-E2 (cover letter attachment) be raised as an immediate follow-on ticket reusing the same mechanism NIC-46 builds, given the two are structurally identical? Recommend yes, as a fast-follow, but not bundled into NIC-46 (ticket title/description is CV-specific).
- **No blockers to starting Builder work.** Credential confirmed live and working; prior-art (block helper, page structure) confirmed by direct code read; OQ-13 confirmed resolved with no contradiction found.

## 11. Go/no-go recommendation

**GO.** All stated dependencies (NIC-43 block helper, NOTION_API_KEY credential, resolved OQ-13/PDF decision) are independently verified, not just assumed. No approval-gate conflict: this is normal feature implementation on the project's own confirmed target architecture (Notion-as-system-of-record + native file attachments + existing skills), matches the "no additional human approval needed" framing in the task context, and I concur — nothing here rises to AGENTS.md's forbidden-operations list (no deployment, no destructive data operation beyond archiving a self-created test artifact, no secret exposure, no third-party contact). Builder should proceed directly.

---

## HANDOFF TO BUILDER

**Objective:** Implement the mechanism that uploads a final tailored-CV PDF as a native Notion `file` block under the "📄 Tailored CV" section of a job's Notion page, replacing the NIC-43 placeholder callout, with exactly one file retained per job at any time (no refinement-draft accumulation).

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2`.
- `scripts/notion_job_page_blocks.py` — existing `build_job_page_children()`; the Tailored CV section is block index 6-7 (0-indexed) in the 14-block array: `heading_2("📄 Tailored CV")` immediately followed by the placeholder `callout`.
- Kanban DB: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`, under Notion page `3ab05073-c5b0-8061-bc12-e92aa903bebc` ("Job Search").
- `notion` skill (file_uploads 3-step flow: `POST /v1/file_uploads` → `PUT` bytes to `upload_url` → reference `file_upload_id` in a `file` block) — `NOTION_API_KEY` confirmed live/working.
- `docs/ARCHITECTURE.md` NIC-42/NIC-43 sections for prior call-shape precedent and documentation format to follow.
- This document (`docs/handoffs/NIC-46-product-planner-scope-validation.md`) for full rationale.

**Constraints:**
- Do not modify `cv-match` (v1 repo) or its output logic/format in any way.
- Do not build a PDF-export step for `cv-match` — use a small synthetic/dummy PDF for verification and say so explicitly in your evidence (do not imply it's a real CV).
- Do not touch any of the 5 live, real job cards found in the Kanban database during investigation (Upslide, InvestHub, Staff CSM, Freelance x2, Implementation Manager - Strategic Accounts) — create and use your own dedicated test card only, referenced by its own hardcoded `page_id`.
- Test/cleanup discipline (mirrors NIC-43 exactly): create one test card with `Name` containing `TEST NIC-46 verification` (and `Company`/`Role` set to `TEST`, `Status: selected`, using `build_job_page_children()` for the initial structure so the placeholder exists to be replaced), attach the synthetic PDF via the real 3-step flow, run `GET /v1/blocks/{page_id}/children` to confirm exactly one `file` block now exists in the Tailored CV section and the old callout is gone/replaced, fetch the file URL to confirm it's downloadable, THEN immediately `PATCH /v1/pages/{page_id}` with `{"archived": true}` and confirm the response. Do not leave the test card live after evidence capture.
- No deployment, no destructive/irreversible operation beyond archiving your own test artifact, no secret exposure, no third-party contact.

**Acceptance criteria:** AC1–AC6 in §7 above (upload+viewable, final-version-only/no-accumulation, PDF format confirmed, correct-page targeting, synthetic-PDF limitation stated honestly, test-artifact archived).

**Files/scripts likely to touch:**
- New script (suggest `scripts/notion_cv_attachment.py` or similar) implementing: (a) the 3-step file upload, (b) locating/replacing the Tailored CV placeholder block for a given `page_id`, (c) the "remove old file block before adding new one" logic for OQ-5.
- `docs/ARCHITECTURE.md` — new "NIC-46" section (call shapes, block-replace logic, evidence).
- `docs/PLAN.md` — new NIC-46 entry recording shipped status, evidence pointer, and explicit out-of-scope confirmations (mirroring NIC-42/43 entries).

**Recommended next action:** Builder implements Option A (block-level `file` object, §6) end-to-end, verifies with the one test card described above, archives it, documents evidence, and hands off to QA Reviewer with: the exact `file_uploads` request/response, the block-list GET before and after (showing callout replaced by file block), the fetched-file confirmation, and the archive confirmation.
