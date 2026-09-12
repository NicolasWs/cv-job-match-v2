# NIC-56 — Product Planner Scope Validation

**Ticket:** NIC-56 — "Input Selected Jobs in Notion from the Saved Jobs in LinkedIn automatically"
**Traces to:** FR-D1–D3 (Notion Kanban Tracker), Section 6.2 non-goals (discovery layer), PRD Section 10 Dependencies
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/implementation performed; this is scope definition only. No LinkedIn access, no browser automation against LinkedIn, and no Notion API calls were made during this investigation — the LinkedIn-access question is decided on ToS/documentation grounds, not by testing live access, and no Notion card creation is authorized at this stage.

---

## 1. Problem restatement

Nicolas maintains a list of jobs he has marked "Saved" on LinkedIn's own tracker page (`linkedin.com/jobs-tracker/?stage=saved`). Today, getting any of those into the Notion Kanban as `selected` cards requires him to manually open the Notion database and create/fill each card by hand (the only entry path that exists right now — no card-creation skill/script exists in this repo yet, per NIC-45's documented "manual-entry gap"). He wants some or all of his LinkedIn-saved jobs (up to "all," minimum "the 5 most recently saved") turned into Notion cards with `Status = selected` automatically, without hand-typing each one.

## 2. Goal

Reduce the friction of getting a LinkedIn-saved job into the Notion pipeline from "manually create and fill a Notion card by hand" to "one low-friction action creates N correctly-structured `selected` cards," while respecting two constraints that are non-negotiable per this repo's governance:
1. Never contact a third party (here: LinkedIn, specifically an authenticated scrape of Nicolas's own account) without explicit human approval (AGENTS.md forbidden-operations rule).
2. Never invent a bespoke access mechanism when a smaller, lower-risk one satisfies the ticket (architecture stays Notion + Claude Code skills + n8n; "smallest viable implementation").

## 3. Facts, assumptions, and findings (separated explicitly)

### 3.1 Facts (verified this session)
- **No card-creation skill/script exists in this repo yet.** Confirmed by reading `docs/PLAN.md` (NIC-44 "conversational Kanban status updates" is still Backlog) and `docs/ARCHITECTURE.md` (NIC-43's own text: "no card-creation skill or conversational entry point built (that's NIC-44)"). This ticket is therefore the **first** ticket in this repo that would create brand-new job cards programmatically, not just update or attach to existing ones — a materially different (higher-stakes, higher-blast-radius) operation than every prior shipped ticket (NIC-42/43/46/47/48), which all operated on cards that already existed or on isolated test cards.
- **`scripts/notion_job_page_blocks.py`'s `build_job_page_children()` exists and is the established convention** for giving any newly-created card the correct 14-block per-job page structure (verified by reading the file's usage in NIC-43/46/47/48's evidence trails). Any card-creation code this ticket eventually produces must call it, per repo convention.
- **The Notion Kanban schema (NIC-42) already supports this ticket's target state with zero schema changes**: `Status` includes `selected` as a valid value; `Name`/`Company`/`Role` are populatable at creation via the existing `POST /v1/pages` call shape documented in NIC-43's ARCHITECTURE.md section.
- **LinkedIn does not offer a public API for reading a member's own saved-jobs list.** Confirmed via web search against LinkedIn's own developer documentation (`learn.microsoft.com/en-us/linkedin/`, `developer.linkedin.com/product-catalog`) and third-party analysis (`linkedapi.io/guides/linkedin-jobs-scraper`, 2026): LinkedIn's public/partner API surface covers Marketing, Talent (employer-side job *posting*, i.e. `Job Posting API` — publishing jobs, not reading a member's saved list), Learning, Sales, and Compliance business lines. There is no documented "Jobs" or "Saved Jobs" read endpoint for a consumer/member account in any of LinkedIn's official API product catalogs. This directly confirms the ticket-context's flagged assumption as a **fact, not a hypothesis to re-verify**.
- **`linkedin.com/jobs-tracker/?stage=saved` requires an authenticated, logged-in session** — it is not a public URL; loading it without Nicolas's own logged-in LinkedIn session returns a login wall (general LinkedIn behavior for member-account pages, consistent with every other authenticated LinkedIn URL; not independently re-tested this session since doing so would itself constitute unauthorized automated access, see §4).
- **AGENTS.md forbidden-operations rule** states explicitly: "No contacting third parties (emails, external APIs with side effects, messages) without explicit human approval." LinkedIn's own User Agreement (publicly known, standard clause across all LinkedIn ToS versions) prohibits automated scraping/data extraction from the platform, including via a browser session logged in as the account holder — this applies regardless of whose data is being read.
- **PRD Section 6.2 (Out of scope)** and the ticket context both correctly note that the existing n8n + `find-opportunities` automated discovery layer (weekly Apify scrape across 4 job boards) is explicitly retained as the *only* automated discovery/import mechanism currently approved in this project's architecture — LinkedIn Saved Jobs is a distinct, second input path not mentioned anywhere in the current PRD.

### 3.2 Assumptions (explicit, not verified by live testing)
- Assumed: "recently saved" ordering, if sourced from a manual export (see §5, Option C/D), will follow whatever order Nicolas's copy/paste or export preserves (LinkedIn's own page order, most-recent-first, is LinkedIn's default sort for the Saved Jobs tab) — not independently re-confirmed by loading the page this session (see §4 on why).
- Assumed: a Notion card counts as a valid, complete `selected` card once `Name`, `Status=selected`, `Company`, and `Role` are populated and the 14-block template is attached (matching the existing `NIC-43`/`build_job_page_children()` convention) — `Priority` is optional/unset unless Nicolas specifies it per job.
- Assumed: deduplication should be checked before creating any card, since this is the first ticket that creates net-new cards and accidental duplicates would pollute the Kanban board immediately with no existing skill to clean them up.

### 3.3 Decisions this scope doc makes (Product Planner judgment calls, flagged as such)
- **This is a net-new input source, not a natural extension of FR-D1–D3.** FR-D1–D3 describe the Kanban's *existence and structure*; they say nothing about *how* a card gets created, and PRD Section 6.2 explicitly scopes automated discovery to n8n/`find-opportunities` only. Recommendation: this ticket should ship as a **small, additive feature** (a manual/semi-automated import helper) rather than requiring a full PRD amendment — but the Product Planner flags this for Boss/Nicolas awareness rather than silently proceeding, because it does introduce a second job-input path the PRD's Section 2/6 narrative doesn't currently describe. A one-paragraph PRD Section 6.1 addendum (not a full rewrite) is the recommended lightweight fix, sequenced as a Builder documentation task, not a blocking prerequisite.

## 4. The critical constraint: third-party/ToS risk (explicit call-out, per task instructions)

**Finding: automated, credential-based scraping of `linkedin.com/jobs-tracker/?stage=saved` is NOT pre-approved by this ticket and MUST NOT be built without a separate, explicit human approval step.**

Reasoning:
- AGENTS.md's forbidden-operations list is unconditional on this point ("No contacting third parties... without explicit human approval") — a Linear ticket description authored before this scoping pass does not constitute that approval; approval must be a distinct, informed decision by Nicolas once he understands what "automated" would concretely mean (a persistent, credentialed browser session acting as him against a platform whose terms prohibit it).
- This is categorically different from every other "third party" this project already touches: the existing n8n/Apify weekly scrape targets public job-board listings, not an authenticated personal account page, and was already resolved/approved in the PRD's Section 1 "Resolved scoping decisions." LinkedIn Saved Jobs has had no equivalent resolution.
- The risk is not hypothetical or merely reputational — LinkedIn has a documented history of enforcement action (account restriction/suspension) against automated access to authenticated pages, even for a user's own data, and technical mitigations (rate-limiting, human-like delays) do not change the ToS violation, only its detectability.

**Recommendation: do not seek approval for full automation (Option a, below) as part of this ticket.** Instead, recommend Nicolas be offered the two lower-risk options (§5, Options C/D) as the actual buildable increment, with Option (a) recorded as a known future possibility **only if** Nicolas later explicitly accepts the ToS/account risk in writing (e.g., a Linear comment or direct confirmation to Boss) — this scope doc does not pre-approve that path and Builder must not implement it without that explicit sign-off landing first.

## 5. Technical access mechanism options (enumerated, with recommendation)

| Option | Mechanism | Automation level | Risk | Verdict |
|---|---|---|---|---|
| (a) Browser automation, logged in as Nicolas | A persistent browser session/cookie automates loading `jobs-tracker/?stage=saved` and scrapes the DOM for job entries | Highest — fully "automatic" per the literal ticket ask | **High** — ToS violation, account suspension risk, requires human approval per AGENTS.md that this ticket does not carry | **Not recommended for this ticket.** Defer; only revisit with Nicolas's explicit, informed written approval as a separate decision. |
| (b) LinkedIn official API | Read saved jobs via a LinkedIn Talent/Consumer API product | Fully automatic, ToS-compliant if the endpoint existed | N/A | **Not available.** Confirmed as a fact (§3.1): no LinkedIn API product exposes a member's own saved-jobs list. Ruled out, not a live option. |
| (c) Semi-automated: Nicolas manually copies/pastes the saved-jobs list (job titles, companies, URLs) as text, an agent/skill parses it and creates Notion cards | Nicolas performs the LinkedIn-side action himself (already logged in, in his own browser, doing nothing LinkedIn's ToS restricts); the agent's job starts only after that point | Semi-automatic — one paste + one command per run, not truly "hands-off" | **Low** — no third-party contact by the agent at all; Nicolas is simply using his own browser as always | **Recommended primary option.** |
| (d) Nicolas exports a saved-search-results file (HTML save, CSV, or copy of the page's visible list) and provides it per run | Same risk profile as (c), different input format | Semi-automatic, same friction level as (c) | **Low**, same reasoning as (c) | **Acceptable alternative to (c)**; recommend letting Builder pick whichever is easier to parse reliably (freeform pasted text vs. a saved HTML/CSV) — Product Planner does not have a strong preference, this is a parsing-format detail, not a scope decision. |

**Recommendation: Option (c), with (d) as an implementation-detail fallback if freeform text parsing proves unreliable.** This is the smallest safe increment: it requires no new credential, no new third-party contact, no PRD non-goal violation, and no human-approval gate beyond what this scope doc itself already grants (Product Planner approval is the required gate for "non-trivial implementation" per FACTORY_PROTOCOL.md's Approval gates section — human/Nicolas approval is specifically called out as required only for the categories AGENTS.md lists, and Option (c)/(d) trigger none of them).

## 6. Scope size: "all or at least the 5 most recently saved"

**Recommended concrete default: process up to the most recent 5 job entries in the order Nicolas provides them** (since under Option c/d, "recently saved" ordering is whatever order appears in Nicolas's copy/paste — LinkedIn's Saved Jobs tab default-sorts most-recent-first, so a straight top-to-bottom read of a freshly-copied list satisfies "most recently saved" without the agent needing its own notion of recency). "All" is supported as an explicit override (Nicolas pastes more than 5 and says "do all of these"), but **the default without an explicit "do all" instruction is 5**, matching the ticket's own stated floor and keeping the smallest safe increment reviewable in one sitting.

**Deduplication rule (recommended, since this is the first card-creation ticket and duplicates cannot yet be cleaned up by any existing tool):** before creating a card, query the existing Notion Kanban database (`POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query`) and skip any input job whose `Company` + `Role` combination (case-insensitive, whitespace-normalized) already exists on a non-archived card, regardless of that card's current status. Report skipped duplicates back to Nicolas rather than silently dropping them, so he can decide whether a real re-application is intended.

## 7. Recommended scope for this ticket (smallest safe increment)

**In scope:**
1. A new script (working name `scripts/notion_import_saved_jobs.py`, final naming at Builder's discretion following existing repo conventions) that:
   - Accepts a freeform text or structured (CSV/list) input of job entries (title/role, company, and ideally a job URL) that Nicolas has manually copied from his own logged-in LinkedIn Saved Jobs tab — the script itself never touches `linkedin.com`.
   - Parses up to 5 entries by default (all entries if the caller explicitly requests it), preserving input order as the "most recently saved" ordering.
   - Deduplicates against existing non-archived Notion cards by `Company`+`Role` (§6), skipping and reporting duplicates rather than creating them.
   - For each non-duplicate entry, creates a Notion card via the existing `POST /v1/pages` shape (per NIC-43's documented convention): `Status = selected`, `Company`, `Role`, `Name` (recommend `"{Company} - {Role}"`, consistent with this repo's existing naming-convention precedent from NIC-48), and the standard 14-block template via `build_job_page_children()`. `Priority` is left unset unless Nicolas specifies one.
   - Reports back: cards created (with Notion page URLs), duplicates skipped, and any entries that failed to parse.
2. A short, one-paragraph addendum to `docs/PRD.md` Section 6.1 (In scope) noting LinkedIn Saved Jobs as an additional **manual/semi-automated** input path alongside the existing n8n discovery layer — explicitly not a PRD rewrite, just a scope note so this input path is documented where a future reader would look for it. (Builder responsibility, following the NIC-42/43/46/47/48 precedent of Builder updating docs, not Product Planner.)
3. `docs/ARCHITECTURE.md` and `docs/PLAN.md` entries documenting the design decision and verification evidence, per established repo pattern.

**Explicitly out of scope for this ticket:**
- Any browser automation or credentialed access to `linkedin.com` in any form (Option a) — requires a separate, explicit human-approval decision not granted by this scope doc.
- Any reliance on a LinkedIn API (Option b) — confirmed unavailable, not a live option.
- Building a general-purpose "any pasted job list" importer beyond LinkedIn Saved Jobs framing — keep the parser scoped to what this ticket needs; a broader importer is a possible future generalization, not this ticket's job.
- n8n involvement of any kind — this is a conversational/manual-trigger skill/script, not an automation-layer (Phase 5) concern; n8n is explicitly sequenced last in the PRD's rollout plan (Section 12) and nothing about this ticket requires disturbing that sequencing.
- Company research briefs, CV/cover-letter attachment, or cheat-sheet generation for the newly-created cards — those are separate, already-scoped Phase 2/3/4 capabilities (NIC-46/47/48 and future company-research tickets); this ticket only creates the bare `selected` card and its empty template, exactly like every card created today would start.

## 8. Acceptance criteria (numbered, testable)

| # | Criterion | Testable check |
|---|---|---|
| AC1 | Given Nicolas provides a manually-copied list of ≥1 LinkedIn saved-job entries (title/company, optionally URL), the script creates Notion cards for up to 5 of them by default, or all of them if explicitly instructed. | Run with a 7-entry synthetic input, no "do all" flag: exactly 5 cards created, in input order; re-run with "do all": all 7 processed (minus any duplicates). |
| AC2 | Every created card has `Status = selected`, and non-empty `Company`/`Role` properties populated from the input. | `GET`/query each created card's properties; all three fields present and non-empty, `Status` exactly `"selected"`. |
| AC3 | Every created card has the standard 14-block template attached (via `build_job_page_children()`), matching NIC-43's established structure — no ad hoc/different template. | `GET /v1/blocks/{page_id}/children` on each created card returns the same 14-block sequence documented in `docs/ARCHITECTURE.md`'s NIC-43 section. |
| AC4 | Entries whose `Company`+`Role` combination already exists on a non-archived Notion card are skipped, not duplicated, and reported to Nicolas by name. | Seed one existing test card with `Company="Acme"`/`Role="PM"`, then attempt an import including an `Acme`/`PM` entry: no second `Acme`/`PM` card is created; the run's output/report explicitly names the skipped duplicate. |
| AC5 | The script never makes any network call to a `linkedin.com` host. | Code review / static check confirms zero `linkedin.com` references or HTTP calls in the script; only Notion API calls are made. |
| AC6 | Malformed or unparseable entries in the input are reported, not silently dropped or fabricated into a card with invented data. | Feed one deliberately malformed line (e.g., missing company); confirm it appears in a "could not parse" report and no card is created for it with a guessed/blank company name. |
| AC7 | Test-artifact discipline: any test card created during Builder's verification is clearly marked (e.g., `"TEST NIC-56 verification"` in `Name`) and archived after evidence capture, exactly matching NIC-43/46/47/48 precedent; the 5 existing real production cards remain untouched (byte-identical `page_id`/`Name`/`last_edited_time` before/after). | Before/after diff of `POST /v1/data_sources/{id}/query {}` on the real cards; explicit archive + follow-up `GET` confirming `archived: true` for every test card. |
| AC8 | No automated/credentialed LinkedIn access of any kind is implemented as part of this ticket. | Code review confirms AC5's zero-`linkedin.com`-calls property; this is the same check restated as an explicit safety criterion, not just a technical one. |

## 9. Effort estimate

**S — approximately 2–3 hours.** Reasoning: this is the first ticket to create *new* cards (higher care needed than NIC-46/47/48's "modify an existing card" pattern — dedup logic and input parsing are net-new logic, not reuse of an existing mechanism), but it reuses the fully-proven `POST /v1/pages` + `build_job_page_children()` call shape from NIC-43 with zero schema changes and no new attachment/upload flow (unlike NIC-46/47's file-upload complexity). Breakdown: input parsing + dedup query logic (~60–75 min, genuinely new), card-creation loop reusing the existing shape (~30 min), verification cycle with synthetic test entries + cleanup (~30–40 min), documentation (~15–20 min). Comparable to NIC-43 (per-job template ticket) in size, slightly larger due to the dedup-safety requirement this ticket adds that NIC-43 didn't need.

This estimate assumes **Option (c)/(d) only** — if Option (a) (automated LinkedIn scraping) is later separately approved, that would be a distinct, larger ticket (M–L: new browser-automation dependency, credential/session handling, DOM-parsing fragility against a platform that can change its markup, and ongoing ToS-risk monitoring) — not an extension of this estimate.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Nicolas's actual expectation is closer to Option (a) ("automatically" was in the ticket title) and Option (c)/(d) may feel like a smaller win than hoped. | Medium — could require a follow-up conversation/ticket if Nicolas pushes back on the semi-automated scope. | This scope doc surfaces the ToS/approval gap explicitly and early (this section + §4) rather than silently downgrading the ask; recommend Boss relay this tradeoff to Nicolas directly rather than assume Option (c) is accepted. |
| Freeform text parsing (Option c) is inherently fragile — LinkedIn's saved-jobs page layout/copy-paste output is not a stable, documented format Product Planner can fully specify in advance. | Medium | Recommend Builder design the parser defensively (AC6: report, don't guess, on anything ambiguous) and pick whichever concrete input format (freeform paste vs. a saved HTML snippet, Option d) proves most reliable during implementation — this is a Builder-level implementation decision, not a blocking scope question. |
| This is the first ticket that creates net-new production cards — a bug in the dedup or parsing logic could pollute the real Kanban board in a way no existing tool can clean up (no "delete card" skill exists yet). | Medium-High | AC4 (dedup) and AC7 (test-artifact discipline, real-cards-untouched diff) are both mandatory acceptance criteria specifically because of this risk; recommend Builder run its full verification cycle against test cards only, exactly as NIC-43/46/47/48 did, before ever running with real LinkedIn-derived input. |
| PRD narrative (Section 2/6) doesn't currently mention LinkedIn Saved Jobs as an input source at all — a future reader could be confused about where this capability "belongs." | Low | §7's recommended one-paragraph PRD Section 6.1 addendum closes this gap without requiring a full PRD amendment/re-approval cycle. |
| LinkedIn's saved-jobs page structure or default sort order could differ from the "most-recent-first" assumption (§3.2), silently changing what "top 5" means. | Low | Not independently verified this session (§3.2, §4) since doing so would require loading an authenticated LinkedIn page — flagged as an open, non-blocking assumption; recommend Builder ask Nicolas to confirm the order of one real paste sample during implementation rather than the Product Planner attempting to verify it via unauthorized access. |

## 11. Open questions

- **OQ-1 (not blocking, recommend Boss relay to Nicolas):** Does Nicolas accept the Option (c)/(d) semi-automated scope (one manual copy/paste per run) as satisfying this ticket, or does he want to formally request the higher-risk Option (a) automated-scraping path as a separate, explicitly-approved follow-up ticket? This scope doc proceeds on the assumption that (c)/(d) is the acceptable default per this ticket's own AC framing and AGENTS.md's approval-gate requirement, but the literal ticket title ("...automatically") suggests this should be explicitly confirmed, not silently assumed away.
- **OQ-2 (not blocking):** Should the one-paragraph PRD Section 6.1 addendum (§7) be written now (Builder, alongside implementation) or held until Nicolas has confirmed OQ-1? Recommend writing it regardless of OQ-1's answer, describing whichever mechanism actually ships — low cost either way.
- **OQ-3 (not blocking):** Exact input format for Option (c) vs (d) — freeform pasted text (title + company, one job per line/block) vs. a saved HTML/CSV export. No strong Product Planner preference; recommend Builder prototype against one real (Nicolas-provided) sample during implementation to pick the more robust format.
- **No blockers to starting Builder work on the recommended (c)/(d) scope.** The only blocker is specifically around Option (a) (full automation), which this scope doc explicitly does not authorize.

## 12. Go/no-go recommendation

**GO — but scoped to Option (c)/(d) only (semi-automated import), NOT Option (a) (automated LinkedIn scraping).** Builder should proceed directly on the manual-paste-then-parse-and-create flow described in §7, which requires no new human-approval gate beyond this scope doc's own Product Planner approval (per FACTORY_PROTOCOL.md's Approval gates section). **Option (a) remains explicitly un-approved** and must not be implemented without a separate, explicit round of human approval from Nicolas that acknowledges the LinkedIn ToS/account-risk tradeoff described in §4 — this is a hard stop, not a recommendation Builder can route around by choosing a "lighter" automation technique (e.g., a headless browser is exactly as prohibited as any other automated access method under LinkedIn's ToS and AGENTS.md's forbidden-operations rule).

---

## HANDOFF TO BUILDER

**Objective:** Implement a semi-automated LinkedIn-Saved-Jobs → Notion `selected`-card importer: Nicolas manually copies his LinkedIn Saved Jobs list from his own already-logged-in browser (no LinkedIn access by the agent/script itself), and a new script parses that input, deduplicates against existing Notion cards, and creates up to 5 (or all, if explicitly requested) new `selected` cards using the existing, proven card-creation shape.

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2`.
- Kanban DB: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`, under Notion page `3ab05073-c5b0-8061-bc12-e92aa903bebc` ("Job Search"). Existing schema: `Name`(title)/`Status`(status, 9 values)/`Company`(rich_text)/`Role`(rich_text)/`Priority`(select) — no schema changes needed.
- `scripts/notion_job_page_blocks.py` — `build_job_page_children()`, must be called for every new card's `children` array, per repo convention (NIC-43/46/47/48 precedent).
- `docs/ARCHITECTURE.md` NIC-43 section for the exact `POST /v1/pages` call shape (`parent.database_id` + `properties` + `children` in one call).
- This document (`docs/handoffs/NIC-56-product-planner-scope-validation.md`) for full rationale, the recommended access-mechanism decision (§5), scope (§7), and testable AC (§8).

**Constraints:**
- **Hard stop: no automated/credentialed access to any `linkedin.com` host, in any form** (no browser automation, no session cookie use, no scraping) — this is not pre-approved by this ticket (§4). Verify with AC5/AC8 (zero `linkedin.com` references in the shipped code).
- New script must accept manually-provided input only (freeform text or a Nicolas-provided export file) — the human-in-the-loop copy/paste step is what keeps this ticket inside the existing approval gates.
- Must call `build_job_page_children()` for every new card — do not invent a different template.
- Must implement the deduplication check (§6) against non-archived existing cards before creating anything.
- Must default to 5 entries unless explicitly told to process all — do not silently process more than 5 without an explicit override signal in the input/invocation.
- Never touch the 5 real production cards except to read them for deduplication comparison — all verification must use dedicated, clearly-marked test cards, archived after evidence capture, mirroring NIC-43/46/47/48's exact discipline (AC7).
- No deployment, no destructive/irreversible operation beyond archiving your own test artifacts, no secret exposure, no third-party contact.

**Acceptance criteria:** AC1–AC8 in §8 above.

**Files/scripts likely to touch:**
- New file: `scripts/notion_import_saved_jobs.py` (or Builder's preferred naming, following existing `notion_*.py` convention).
- `docs/PRD.md` — one-paragraph Section 6.1 addendum noting this new manual/semi-automated input path (§7, §11 OQ-2).
- `docs/ARCHITECTURE.md` — new "NIC-56" section (design decision, call shape, dedup logic, verification evidence).
- `docs/PLAN.md` — new NIC-56 entry, mirroring the existing format.

**Recommended next action:** Builder implements the Option (c)/(d) semi-automated importer only, runs the full test-card verification cycle (dedup check, 5-vs-all limiting, malformed-input reporting, real-cards-untouched diff), documents evidence, and hands off to QA Reviewer. If Nicolas later wants to pursue Option (a) (automated scraping), that requires a new, separate Linear ticket explicitly authorized by Nicolas after reviewing the ToS/account-risk tradeoff in §4 of this document — Boss should not route that request to Builder without that explicit sign-off landing first.
