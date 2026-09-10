# NIC-43 (P1-T2) — Product Planner Scope Validation

**Ticket:** NIC-43 — "P1-T2 — Per-job Notion page template (job details, research, CV, cover letter, cheat sheet)"
**Traces to:** FR-D3, US-2 (docs/PRD.md)
**Depends on:** P1-T1 / NIC-42 (Notion Kanban database) — **Done**
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/content implementation performed; this is scope definition only.

---

## 1. Problem

Each job pursued through the pipeline needs one place — a job's Notion page — that surfaces everything relevant to that application: the job itself, company research, the tailored CV, the cover letter, and the interview cheat sheet. Today (post-NIC-42), the Kanban database schema exists (`database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, under "Job Search" page `3ab05073-c5b0-8061-bc12-e92aa903bebc`) but **no job card/page has ever been created** (confirmed in `docs/PLAN.md` NIC-42 and NIC-45 entries — schema-only, no seed data, no card-creation skill exists yet in this repo). So there is currently no defined page structure at all: if a card were created today (manually, via the Notion UI, the only method available per NIC-45 §"Interim manual-entry gap"), its page would be blank. Nicolas would have to build the five-section layout by hand, every time, or scatter content across tools — exactly what US-2 and FR-D3 exist to prevent.

## 2. Objective

Define the exact structure and creation mechanism for a per-job Notion page so that opening any job's card page shows five clearly labeled sections — job details, company research brief, tailored CV, cover letter, interview cheat sheet — in a single scannable place, even when later-stage sections are still empty, and so that this structure appears automatically whenever a new job card is created (not as a manual per-card formatting chore).

## 3. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` — pipeline rules, handoff contract, Linear lifecycle.
- `docs/PRD.md` — FR-D3 (line 138), US-2 (line 262, "Recommend a Notion page template applied on card creation"), US-1/FR-D1-D2 context, §9 UX ("research brief → CV → cover letter → cheat sheet, top to bottom"), §12 Rollout Phase 1 note ("+ per-job page template under the existing 'Job Search' page").
- **OQ-13 (resolved on NIC-40):** target file format for native Notion CV/cover-letter attachments is **PDF**. This directly shapes the CV and Cover Letter sections below (they will eventually hold PDF file blocks, not Markdown/DOCX).
- **OQ-14 (resolved on NIC-41):** 12-month recency window for "recent" company research signals (YouTube video, news). Does not change this ticket's page *structure*, but confirms the Company Research section will eventually carry dated, time-boxed content once Phase 3 (`company-research` skill) ships.
- `docs/ARCHITECTURE.md` — NIC-42 data model (`Name` title, `Status` status/9 values, `Company` rich_text, `Role` rich_text, `Priority` select) and the documented API limitation: **the Notion REST API cannot create/configure database views** (Kanban board view is a manual UI step). This is directly relevant by analogy (see §6 below — native page *templates* have the same kind of API gap).
- `docs/PLAN.md` — NIC-42 (Done, schema only, zero cards created — explicit no-fabrication decision), NIC-45 (confirms no card-creation skill exists yet anywhere in this repo; "tracking in Notion" today means manual UI card creation).

## 4. Constraints (carried from AGENTS.md / FACTORY_PROTOCOL.md)

- Product Planner does not implement code or write to Notion — scope definition only.
- No destructive operations, no data deletion without explicit human approval, no secrets exposed, no third-party contact.
- v2 repo and Notion workspace only — v1 production repo (`/home/nicow/cv-job-match`) is untouched by this ticket.
- No fabricated data: any verification card Builder creates to prove the template works must be clearly marked as a test artifact and removed (archived, not permanently deleted) after verification — mirrors the no-fabrication discipline already applied in NIC-42.
- CV/cover-letter file sections must be designed around **PDF** as the eventual attachment format (OQ-13/NIC-40), even though the actual files aren't produced until Phase 2/3 work ships.

## 5. Scope — what NIC-43 delivers

**In scope:**
1. A defined, reusable **block structure** (Notion API block objects) representing the five sections, in the order specified by FR-D3/the ticket: Job Details → Company Research Brief → Tailored CV → Cover Letter → Interview Cheat Sheet.
2. A defined **application mechanism**: how that block structure gets attached to a job's page automatically whenever a new card is created (see §6 — this cannot be a native Notion "page template" applied via the API; it must be applied programmatically as part of card creation).
3. One-time verification: Builder creates a single test card using the mechanism above, confirms all five sections render correctly via the API, then archives (soft-deletes, reversible) the test card — no permanent fabricated data left behind.
4. Documentation in `docs/ARCHITECTURE.md` of the block schema, the creation call shape, and the known limitation described in §6.

**Out of scope (explicitly, for this ticket):**
- Actually populating any section with real content (company research text, CV file, cover letter file, cheat sheet content) — those are Phase 2/3/4 work (PLAN.md rollout phases), not this ticket.
- Building a "create job card" skill or conversational entry point — that is NIC-44 (conversational Kanban status updates) or a future ticket; NIC-43 only defines what structure gets applied *when* a card is created, not the trigger/UX for creating one.
- Changing the NIC-42 database schema (Name/Status/Company/Role/Priority) — adding new properties (e.g., a Job URL or JD-paste property) is a separate decision; flagged as an open question below, not authorized here.
- Any n8n automation (Phase 5, FR-G) — untouched by this ticket.
- Seeding real job cards with real pipeline data.

## 6. Key design decision: no native Notion "page template" via the API

The ticket text (and US-2's technical note) references a Notion "page template applied on card creation." This needs to be scoped precisely because the natural reading — a native Notion **database template** configured via the "+ New" button's template picker in the Notion UI — **cannot be created or assigned via the Notion REST API**. This is the same category of gap NIC-42 already hit for Kanban board views (documented in `docs/ARCHITECTURE.md`: "Managing views is not currently supported in the API"); Notion's API has no `templates` endpoint at all as of API version `2025-09-03`.

**What the API *can* do:** `POST /v1/pages` (used to create each new database row/card) accepts an optional `children` array of block objects in the *same call* that creates the page and sets its properties. This means the five-section structure can be attached atomically at creation time — but only for cards created **through the API**, not for cards a human creates by clicking "+ New" in the Notion UI.

**Recommendation (two-track, so AC3 is genuinely satisfied both today and going forward):**

- **Track A (primary deliverable, required):** Builder implements a reusable function/script (e.g. a small Python helper or a documented block-JSON template in the repo) that produces the five-section `children` block array, and wires it into the `POST /v1/pages` call used whenever a job card is created via the API. Any future automated or skill-driven card creation (NIC-44 or a later ticket) calls this same helper, guaranteeing every API-created card gets the structure automatically, with no per-card manual formatting. This is the mechanism that actually satisfies "applied automatically to card creation" in a way the API can enforce.
- **Track B (recommended, manual, non-blocking):** Builder additionally configures a matching **Notion-native database template** by hand in the Notion UI (mirroring the same five sections), exactly as NIC-42 left the Kanban board view as a flagged manual step. This covers the *current* manual-card-creation workflow (per NIC-45, there is still no automated card-creation skill in this repo) so that if Nicolas clicks "+ New" and picks the template today, he gets the same structure without waiting for a future automation ticket. This is a nice-to-have, not required for NIC-43 to be considered done, and should be flagged in Builder's handoff as a manual step outside API control (same class of caveat as the NIC-42 board-view gap) — not silently claimed as "automatic."

This distinction must be stated explicitly in Builder's evidence so QA Reviewer does not mistake Track B (a manual, human-performed Notion UI action) for an automated guarantee.

## 7. Proposed Notion block structure (per section)

All sections use the same pattern: a `heading_2` block labeling the section, followed by placeholder content when the source data doesn't exist yet, with a `divider` block between sections for visual scanability. Order matches FR-D3's listed order.

| # | Section | Blocks | Empty-state behavior (AC2) |
|---|---|---|---|
| 1 | **Job Details** | `heading_2` "📋 Job Details" + `paragraph` placeholder (e.g. "Add job description / posting link here") | Always present at creation; freeform text is fillable immediately (no upstream dependency), so not really "empty pending later stages" — but still rendered as a labeled section per AC1. |
| 2 | **Company Research Brief** | `heading_2` "🔍 Company Research Brief" + `callout` (🕒 icon, gray background) "Pending — populated by the `company-research` skill (Phase 3, not yet built). Will include company summary, recent video, headcount by country, and recent news within a 12-month window (OQ-14)." | Section heading + callout always visible even though Phase 3 hasn't shipped — satisfies AC2 directly. |
| 3 | **Tailored CV** | `heading_2` "📄 Tailored CV" + `callout` (📎 icon, gray background) "Pending — PDF file will be attached here once `cv-match` output is filed (Phase 2). Target format: PDF (OQ-13/NIC-40)." | Same pattern; a Notion `file` block requires an actual file source at creation, so an "empty" file block isn't possible — the callout is the correct empty-state placeholder until Phase 2 replaces/appends a real `file` block. |
| 4 | **Cover Letter** | `heading_2` "✉️ Cover Letter" + `callout` (📎 icon, gray background) "Pending — PDF file will be attached here once `write-outreach` output is filed (Phase 2). Target format: PDF (OQ-13/NIC-40)." | Same as #3. |
| 5 | **Interview Cheat Sheet** | `heading_2` "🎯 Interview Cheat Sheet" + `callout` (🕒 icon, gray background) "Pending — generated once this job reaches an interview stage (Phase 4)." | Same pattern; matches FR-F1/F2 (cheat sheet only generated at interview stage). |

Divider (`divider` block) inserted after each section except the last, for a total of 5 headings + 5 placeholder/content blocks + 4 dividers = 14 blocks in the initial `children` array.

**Why `callout` and not just a `paragraph` for the pending sections:** a callout block visually distinguishes "this is a placeholder, not forgotten/blank content" from a genuinely empty page — this is what makes AC2 ("sections display even when empty") verifiable by inspection rather than ambiguous (an empty paragraph is indistinguishable from a rendering bug; a callout with explanatory text is not).

## 8. Acceptance criteria (validated, restated as testable)

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | Opening any job card's page shows all five sections (Job Details, Company Research Brief, Tailored CV, Cover Letter, Interview Cheat Sheet) in one place, in the specified order, without switching tools. | FR-D3, ticket AC1 | `GET /v1/blocks/{page_id}/children` on a card created via the Track A mechanism returns exactly 5 `heading_2` blocks with the specified text, in order, interleaved with placeholder/callout blocks and dividers. |
| AC2 | Sections render even when their upstream content doesn't exist yet (research/CV/letter/cheat sheet not yet generated). | FR-D3, ticket AC2 | On a freshly created card (no Phase 2/3/4 work run against it), all 5 section headings are present and sections 2–5 show their placeholder `callout` text, not blank space or missing blocks. |
| AC3 | The structure is applied automatically at card creation, not as a manual per-card formatting step. | ticket AC3, US-2 | For **API-driven** creation (Track A): a single `POST /v1/pages` call with `properties` + `children` in the same request produces a fully-structured page — no separate follow-up call needed, no manual editing. Verified by Builder creating one test card this way and inspecting the response/children in the same evidence step, then archiving it. For **manual UI** creation (Track B, non-blocking): documented as "available if the human selects the configured Notion template from + New," explicitly not claimed as automatic since the API cannot enforce it. |

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| AC3 as literally written ("applied automatically") can only be *guaranteed* for cards created through the API. Manual UI card creation (still the only card-creation path that exists in this repo today, per NIC-45) will not automatically get the structure unless the human explicitly picks a Notion-native template from the UI. | Medium — could create a false impression that "automatic" means "even manual clicks get it for free." | Explicitly split into Track A (API, guaranteed) / Track B (UI template, manual, optional) in Builder's evidence; do not claim Track B as automated. Flag to Nicolas that full automatic coverage arrives once a card-creation skill/automation (NIC-44 or later) exists and calls Track A's helper. |
| `file` blocks cannot exist "empty" in the Notion API — CV/Cover Letter placeholders must use `callout`/`paragraph` blocks now, then be **replaced or appended** by a real `file` block once Phase 2 ships. | Low–Medium | Document this explicitly so Phase 2 Builder work knows it must locate and replace/append near the placeholder callout, not assume a pre-existing empty file block. |
| No card-creation skill exists yet in this repo (confirmed NIC-45) — so Track A's helper will exist as reusable code/logic but has no caller in production until NIC-44 or a future ticket builds one. | Low | Explicitly scoped out of NIC-43 in §5; Builder should still verify Track A end-to-end with one test card (proving the helper works), even though nothing calls it automatically in production yet. |
| Adding a Job Details freeform text block invites inconsistent manual content per card (no enforced structure for JD text/link) since no `Job URL`/JD property exists in the NIC-42 schema. | Low | Flagged as OQ-1 below; not blocking — the placeholder paragraph is sufficient for NIC-43's AC1/AC2, structured JD capture can be a later schema addition if desired. |
| Verification card, if not properly archived, becomes fabricated seed data violating the same no-fabrication discipline NIC-42 established. | Low | Builder must archive (`archived: true`, reversible) the test card immediately after capturing evidence, and state this explicitly in the handoff — same as constraint in §4. |

## 10. Open questions

- **OQ-1 (not blocking):** Should a `Job URL` (or JD-paste) rich_text/url property be added to the NIC-42 schema so the "Job Details" section can pull structured data instead of a freeform placeholder paragraph? Additive schema change, low risk, but is a decision outside NIC-43's stated scope (NIC-42 is marked Done) — recommend a follow-up ticket if desired, not addressed here.
- **OQ-2 (not blocking):** Should Track B (manual Notion-native template configuration) be required before NIC-43 is considered fully done, or is it acceptable as a documented, non-blocking manual follow-up (as NIC-42 treated the Kanban board view)? Recommend treating it the same way — non-blocking, explicitly flagged, matching established precedent in this repo.
- **No blockers to starting Builder work.**

## 11. Effort estimate

**S/M — approximately 3–4 hours.** Breakdown: block-structure design/JSON authoring (~45 min, largely done in this document already), Track A implementation (`pages.create` with `children`, reusable helper) (~1–1.5h), one verification test card create/inspect/archive cycle with evidence capture (~45 min), optional Track B manual Notion UI template configuration + documentation (~30–45 min), `docs/ARCHITECTURE.md`/`docs/PLAN.md` evidence write-up (~30 min). Comparable in size to NIC-45 (S, ~1.5–2h) but slightly larger due to the block-schema design work and the two-track creation-mechanism nuance.

## 12. Recommended next action — handoff to Builder

1. Implement **Track A**: a reusable block-structure helper (script or well-documented inline JSON in the repo) producing the 14-block `children` array from §7, called as part of the same `POST /v1/pages` request that creates a job card (`parent.data_source_id = 47340a66-9e15-4ea1-8edf-45bba44c2334`, under the NIC-42 Kanban database) with `properties` set for `Name`/`Status`/`Company`/`Role`/`Priority`.
2. Verify end-to-end with exactly **one** test card: create it via the helper, run `GET /v1/blocks/{page_id}/children` to confirm all 5 headings + placeholders + dividers are present and correctly ordered, capture this as evidence, then **archive** the test card (`PATCH /v1/pages/{page_id}` with `archived: true`) — do not leave it live. State this cleanup explicitly in the handoff.
3. (Recommended, non-blocking) Configure **Track B**: a matching Notion-native database template in the Notion UI mirroring the same five sections, documented as a manual step (same category as NIC-42's Kanban board-view gap) — not claimed as API-automated.
4. Document the block schema, the `pages.create` call shape, and the Track A/Track B distinction in `docs/ARCHITECTURE.md` (new "NIC-43" section, same format as the existing NIC-42 section) and record shipped status in `docs/PLAN.md`.
5. Do not build a card-creation skill/trigger, do not touch the NIC-42 schema, do not populate real section content, do not touch n8n — all explicitly out of scope per §5.
6. Hand off to QA Reviewer with evidence: the exact `children` JSON sent, the `pages.create` response, the `blocks/children` GET confirming structure, and confirmation the test card was archived (not left as fabricated data).
