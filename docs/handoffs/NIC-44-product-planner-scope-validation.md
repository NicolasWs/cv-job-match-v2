# NIC-44 (P1-T3) — Product Planner Scope Validation

**Ticket:** NIC-44 — "P1-T3 — Conversational Kanban status updates"
**Traces to:** FR-D4, US-3 (docs/PRD.md)
**Depends on:** P1-T1 / NIC-42 (Notion Kanban DB schema) — **Done**
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/skill implementation performed; this is scope definition only.

---

## 1. Problem

Once a job card exists on the "Job Search Kanban" Notion database (NIC-42, Done), the only way to move it through the pipeline today is manually clicking through the Notion UI. This breaks the conversational operating model the rest of the repo already uses (v1's README/CLAUDE.md: "add Amundi to my target companies", "switch my CV to French" — plain-English requests that directly edit the underlying system of record). FR-D4 and US-3 require the same conversational pattern for Kanban status: e.g. "mark Mistral as applied" should update that job's `Status` property on Notion, and nothing else.

The two hard risks named in the ticket are the actual crux of the scope:
1. **Ambiguity** — "Mistral" or "the PM role" must resolve to exactly one Notion card via the `Company`/`Role`/`Name` text properties, which are free text, not a unique key.
2. **False positives** — a wrong resolution silently updates the wrong card's status, which is worse than doing nothing, because it corrupts pipeline state invisibly.

## 2. Objective

Define a precise, testable mechanism for natural-language Kanban status updates that (a) resolves a request to the correct card with an explicit ambiguity/not-found fallback, (b) writes **only** the `Status` property, and (c) matches the existing one-shot conversational interaction style — so Builder can implement it without further scope negotiation.

## 3. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` (handoff contract, Linear lifecycle, forbidden operations).
- `docs/PRD.md` — FR-D4, FR-D2 (9 exact status values), US-3, Section 9 (conversational interaction model, "mark this as applied" example), Section 10 (Notion API dependency), Section 11 (risks table).
- `docs/ARCHITECTURE.md` — NIC-42 evidence: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`, parent page `3ab05073-c5b0-8061-bc12-e92aa903bebc`, property schema (`Name` title, `Status` status w/ 9 values, `Company` rich_text, `Role` rich_text, `Priority` select), and the confirmed fact that all four non-title properties are independently filterable via `POST /v1/data_sources/{id}/query`.
- `docs/PLAN.md` — NIC-42 done (schema only, zero cards exist yet); NIC-45 handoff explicitly names NIC-43/NIC-44 as the two tickets that will close the "manual card creation" gap.
- `docs/handoffs/NIC-45-product-planner-scope-validation.md` — precedent for how this factory treats v1-repo edits (v1 = active production pipeline; the prior Product Planner and Builder treated any edit there, even additive, as needing explicit flagging/human awareness before Builder starts).
- v1 repo (read-only, `/home/nicow/cv-job-match`): `README.md`, `CLAUDE.md` (the exact "add Amundi to my target companies" conversational pattern this ticket must match), and all five `.claude/skills/*/SKILL.md` files, in particular `run-my-week/SKILL.md` (the only existing orchestrator skill, and the closest analog to "where would a new skill live").
- This repo (`cv-job-match-v2`) has **no `.claude/skills/` directory of its own** — confirmed by listing the repo tree (only `AGENTS.md`, `README.md`, `docs/`, `bots/*/SOUL.md`). It is currently a docs/planning repo, not a runtime skill repo. This is a load-bearing fact for the architecture decision in Section 5.

## 4. Scope

### 4.1 In scope
- Design (not build) of a resolution mechanism: natural-language company/role reference → unique Notion card (`page_id`) on the Job Search Kanban database.
- Design of a natural-language → canonical status mapping covering the 9 exact values: `selected, cv scored, cover letter done, applied, first interview, second interview, offer, rejected, withdrawn`.
- Design of the write guardrail: the Notion mutation must touch only the `Status` property.
- Design of ambiguous-match and no-match fallback behavior (ask, never guess).
- The architecture decision: new dedicated skill vs. extending an existing skill, and where that skill file physically lives (v1 vs v2 repo) — see Section 5, explicitly called out per the task's constraint that the PRD does not yet resolve this.
- Acceptance criteria Builder must satisfy, written to be independently verifiable by QA Reviewer without re-implementing anything.

### 4.2 Out of scope (explicitly, for this ticket)
- Any code, skill file, or SKILL.md content — Product Planner does not implement.
- Creating any Notion cards/pages (no seed data exists yet; NIC-43 owns per-job page creation, not this ticket).
- The n8n Kanban-triggered automation (FR-G / Phase 5) — status *changes triggering downstream work* is a separate ticket; this ticket only covers the *status write itself*, conversationally initiated by the human.
- Any change to `run-my-week`'s own logging step (that is NIC-45's scope, already handed off).
- Editing any file in the v1 repo — this ticket produces a scope document only; Builder will be the one to touch v1 (if that is the confirmed location), and only after this document's recommendation is accepted.

## 5. Architecture decision: new skill, not an extension of `run-my-week`

**Decision: build a new, small, standalone skill** (working name: `kanban-status`, alternatively `update-job-status`) rather than extending `run-my-week` or any other existing skill.

**Why not extend `run-my-week`:**
- `run-my-week` is a heavyweight, multi-stage *orchestrator* invoked by "run my week" / "run the pipeline" — it scans, checkpoints, builds packages, and logs. A one-line status update ("mark Mistral as applied") has nothing in common with that trigger phrase or that stage machine; bolting it on would force users to invoke pipeline language for an unrelated, instant action.
- The existing conversational-edit pattern this ticket must match ("add Amundi to my target companies") is **not** part of any skill at all in v1 — it's a standing instruction in `CLAUDE.md`/`README.md` to just edit `config/search-profile.yaml` directly when asked. That works for a local YAML file with no remote API, ambiguity, or false-positive risk. A Notion status update needs deterministic query/filter logic, an enum mapping table, and an explicit guardrail — that requires a dedicated, documented procedure, i.e., a skill, not a loose instruction.
- Precedent in the same repo: `interview-prep`, `cv-match`, `write-outreach` are each single-purpose skills; `run-my-week` composes them but doesn't contain their logic. Status update should follow the same single-purpose pattern.

**Where the skill file lives — flagged explicitly (not yet resolved in the PRD):**
`cv-job-match-v2` has no skills directory; the only place Nicolas currently invokes Claude Code skills conversationally is the v1 repo's `.claude/skills/`. Recommendation: **add the new skill as a net-new file at `/home/nicow/cv-job-match/.claude/skills/kanban-status/SKILL.md`** (v1 repo), because:
- It is additive only (a brand-new file, no existing skill logic modified) — lower risk than NIC-45's in-place edit to `run-my-week/SKILL.md`, which the factory already treated as sensitive because v1 is the active production pipeline.
- It is the only place Nicolas's Claude Code sessions currently discover skills from.

This is still a v1-repo touch, so per the AGENTS.md/FACTORY_PROTOCOL.md caution already established by NIC-45's handling, **flag this to Boss/Nicolas for explicit awareness before Builder starts** (not necessarily a hard approval gate the way data deletion is, since it's additive and non-destructive to any existing file — but the precedent in this factory has been to surface any v1-repo write plan before Builder executes it). This is captured as Open Question OQ-1 below; it does not block Product Planner's scope validation, only Builder's start.

## 6. Proposed mechanism (detailed)

### 6.1 Resolution: natural-language reference → unique Notion `page_id`

1. Parse the user's request into two parts: an **entity reference** (company name and/or role, e.g. "Mistral", "the Danone PM role") and a **target status phrase** (e.g. "applied").
2. Query the Job Search Kanban data source (`data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`) via `POST /v1/data_sources/{id}/query` using `rich_text: { contains: "<term>" }` filters on `Company` and, if present, `Role`, plus a `title: { contains: "<term>" }` filter on `Name` as a fallback/combination — filter matching should be case-insensitive substring, consistent with how NIC-42 already verified these three properties are queryable.
3. Classify the result set:
   - **Exactly 1 match** → proceed to write (Section 6.3), then confirm back to the user by name.
   - **0 matches** → no write; tell the user explicitly no matching card was found and name the (sub-)term searched. Never fabricate or guess a card.
   - **2+ matches** → no write; list the candidates (Name / Company / Role / current Status) and ask the user to pick one, or to restate the request with a more specific role. This is the primary false-positive mitigation.
4. If the user supplied both a company and a role fragment (e.g., "mark the Mistral PM role as applied"), require both filters to match before treating it as a single unique hit — a company-only match that returns 2+ rows must not be silently narrowed by a role guess.

### 6.2 Natural-language status phrase → one of the 9 canonical values

Maintain an explicit synonym table (Builder documents this in the skill file), mapping only to the 9 exact enum strings — never a variant, never invented casing:

| Canonical value | Example accepted phrases |
|---|---|
| `selected` | "mark as selected", "add to pipeline" (rare — normally set at card creation) |
| `cv scored` | "cv scored", "cv done", "cv is ready" |
| `cover letter done` | "cover letter done", "cover letter ready", "letter finished" |
| `applied` | "applied", "mark as applied", "I applied", "sent the application" |
| `first interview` | "first interview", "phone screen", "got a call", "screening call scheduled" |
| `second interview` | "second interview", "next round", "final round" (only if the user hasn't already reached `second interview` — ambiguous phrases like "final round" should be flagged rather than auto-mapped if the current status is unclear) |
| `offer` | "offer", "got an offer", "they offered" |
| `rejected` | "rejected", "turned down", "didn't get it", "no go" |
| `withdrawn` | "withdrawn", "pulled out", "no longer interested", "I withdrew" |

**Guardrail:** if the requested phrase does not map unambiguously to exactly one of the 9 values, do not write. Respond listing the 9 valid values and ask the user to clarify. This prevents inventing a 10th status or silently rounding to the "closest" one.

### 6.3 Write guardrail — Status only, nothing else

The Notion mutation is `PATCH /v1/pages/{page_id}` (the page corresponding to the resolved card). The `properties` object in that request body must contain **exactly one key: `Status`**, e.g.:
```json
{ "properties": { "Status": { "status": { "name": "applied" } } } }
```
- `Name`, `Company`, `Role`, `Priority` must never appear in this payload, even with their existing unchanged values — Notion's PATCH semantics only touch keys present in the request, so omitting them is both necessary and sufficient to satisfy "no other field is modified."
- Builder must not read-then-rewrite the full property set "for safety" — that pattern is exactly what risks accidental overwrites (e.g., stale `Priority` reverting a manual edit made between read and write). Single-property PATCH only.

### 6.4 Confirmation / interaction style (US-3)

Match the existing one-shot pattern (no multi-turn form for the common case):
- Unique match + valid status phrase → perform the update immediately, then reply in one line naming what changed, e.g.: "Marked **Mistral — Product Manager** as `applied` (was `cover letter done`)." Including the *old* value in the confirmation is a lightweight audit signal that lets Nicolas immediately notice a wrong-card update, addressing the false-positive risk without adding a pre-write confirmation step for the unambiguous case.
- Ambiguous or not-found → the single short clarifying question described in 6.1/6.2, no update performed.

## 7. Acceptance criteria (Builder-facing, independently verifiable)

| # | Criterion | Traces to | How QA verifies |
|---|---|---|---|
| AC1 | A natural-language status request that uniquely resolves to one card results in exactly one Notion `PATCH /v1/pages/{page_id}` call, and the card's `Status` value after the call equals the mapped canonical value. | FR-D4 AC1 | Re-query the page via `GET /v1/pages/{page_id}` before and after; `Status` differs only as expected. |
| AC2 | The `PATCH` request body's `properties` object contains only the `Status` key. | FR-D4 AC2 | Inspect Builder's logged request payload (evidence requirement per FACTORY_PROTOCOL.md); confirm no other property key present. |
| AC3 | `Name`, `Company`, `Role`, `Priority` values for the affected page are byte-identical before and after the update. | FR-D4 AC2 | `GET /v1/pages/{page_id}` diff before/after on all four fields. |
| AC4 | A request matching 0 cards produces no Notion mutation call and an explicit "not found" response naming the search term. | Section 6.1 (risk mitigation) | Check Builder's call log has zero `PATCH`/`pages.update` calls for that turn. |
| AC5 | A request matching 2+ cards produces no Notion mutation call and a response listing all matched candidates (Name/Company/Role/current Status). | Ticket risk: false positives | Same call-log check as AC4; response must enumerate the actual matches (no fabricated candidate list). |
| AC6 | A status phrase that does not map to one of the 9 canonical values produces no Notion mutation call and a response listing the 9 valid values. | FR-D2 consistency | Same call-log check; response text contains the 9 exact strings. |
| AC7 | The single-hit success response names the resolved card (Company/Role or Name) and both the old and new Status values. | US-3 (interaction style, false-positive visibility) | Manual read of the skill's response text against the actual before/after Status. |
| AC8 | The skill is invocable as a standalone one-shot request (not requiring `run-my-week` or any other orchestrator to be running). | US-3 | Manual test: invoke the phrase directly in a fresh session with no prior pipeline state. |

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free-text `Company`/`Role`/`Name` properties have no uniqueness constraint — two cards can legitimately share a company name (e.g., reapplying to the same company for a different role later). | High (this is the ticket's named false-positive risk) | Mandatory ambiguous-match fallback (AC5); require combining company+role terms when both are supplied (Section 6.1.4); never auto-pick the "most recent" or "first" match. |
| Notion `rich_text.contains` filter case-sensitivity/behavior is not yet empirically confirmed against this specific data source (NIC-42's evidence tested `contains` with exact-case sample data only). | Medium | Builder must verify actual case-insensitivity behavior with a real query during implementation and document it in ARCHITECTURE.md; if case-sensitive, normalize casing before filtering. |
| A status phrase could be genuinely ambiguous relative to the *current* status of the resolved card (e.g., "final round" could mean `second interview` for one candidate's process but something else for another) — guessing wrong silently violates AC1's "correct" requirement even with a unique card match. | Medium | Treat unmapped/ambiguous status phrases the same as AC6 (ask, don't guess), even when the card itself is unambiguous. |
| No Notion write access has yet been exercised from a v1-repo-based skill (v1's skills currently touch Drive/Apify, not Notion) — credential/integration wiring for v1 to call the Notion API is an unverified dependency, mirrors PRD Section 10's dependency note. | Medium | Builder confirms Notion integration token availability/scope for the v1 execution context before writing the skill; if unavailable, this is a blocker to flag back to Boss, not something to route around by inventing a credential. |
| Touching the v1 repo (even additively, a new file) is a repo the factory has previously treated with extra caution (NIC-45 precedent). | Low–Medium (process risk, not technical) | Flagged as OQ-1 below; recommend Boss/Nicolas sign off on "new skill file in v1" before Builder starts, consistent with prior handling. |
| The 9-value enum could silently grow inconsistent if Builder's synonym table diverges from the exact values recorded in ARCHITECTURE.md/NIC-42. | Low | Skill file must hard-code the 9 values as literal constants pulled from this document/ARCHITECTURE.md, not re-derived or paraphrased. |

## 9. Open questions

- **OQ-1 (flag before Builder starts, not a hard blocker):** Confirm with Boss/Nicolas that adding a new skill file to the v1 repo (`/home/nicow/cv-job-match/.claude/skills/kanban-status/SKILL.md`) is acceptable, given v1 is the active production pipeline. Recommendation stands (Section 5) but this factory's own precedent (NIC-45) treats any v1 write as worth explicit surfacing first.
- **OQ-2:** Should ambiguous "final round"-style status phrases ever be resolved automatically using the card's *current* status as context (e.g., only `second interview` is a valid next step from `first interview`)? Recommendation for v1 of this skill: no — always ask rather than infer from current state, to keep the guardrail simple and auditable; revisit if this proves annoying in practice.
- **OQ-3:** Confirm Notion integration credential availability/scope for the v1 execution context (see Risks). Not yet verified in this session (Product Planner does not hold or test credentials).
- **No blockers to starting Builder work** once OQ-1 is acknowledged.

## 10. Effort estimate

**S (small), ~3–5 hours.** Rationale: no new infrastructure and no data model changes (schema already exists from NIC-42), but unlike NIC-45 (pure text edits) this requires: authoring a new SKILL.md with concrete resolution/mapping/guardrail logic, exercising real Notion API calls (query + single-property patch) to empirically confirm filter behavior (case-sensitivity, multi-filter `and` combination), and testing the ambiguous/not-found/invalid-status fallback paths against at least a couple of seeded test cards.

## 11. Recommendation for Builder

1. Get OQ-1 acknowledged (v1-repo new-file location) before starting.
2. Create `/home/nicow/cv-job-match/.claude/skills/kanban-status/SKILL.md` (or agreed alternative path) implementing Sections 6.1–6.4 above, hard-coding the 9 canonical status values and the synonym table from Section 6.2.
3. Implement resolution via `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` (Company/Role/Name filters), and the write via single-property `PATCH /v1/pages/{page_id}` exactly as in Section 6.3 — no read-modify-rewrite of the full property set.
4. Test against a small number of manually-created seed cards (not fabricated production data) covering: unique match, 0 matches, 2+ matches (same company different role), and an unmapped status phrase — report each as evidence per FACTORY_PROTOCOL.md's "Builder must report tests and command results."
5. Do not wire this into `run-my-week` or any n8n automation (both out of scope, Section 4.2).
6. Hand off to QA Reviewer with the AC1–AC8 table above as the verification checklist; QA should independently re-run at least the ambiguous-match and guardrail-payload checks itself (AC2, AC5, AC6), not accept Builder's self-report alone, per FACTORY_PROTOCOL.md's independence rule.
