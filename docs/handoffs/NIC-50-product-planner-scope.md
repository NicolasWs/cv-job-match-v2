# NIC-50 (P3-T2) — Product Planner Scope Validation

**Ticket:** NIC-50 — "P3-T2 — company-research skill: recent YouTube video lookup"
**Traces to:** FR-A3, US-4 (docs/PRD.md)
**Depends on:** P3-T1 / NIC-49 ("New company-research skill: company/website summary") — **still Todo/In Progress, not yet shipped as of this scope doc**
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-12
**Role boundary respected:** no code/implementation performed; this is scope definition only.

---

## 1. Problem

Once a job reaches `selected` status, Nicolas wants a company research brief that includes the most recent relevant YouTube video about the company — a signal of current hiring/brand/product activity — without having to search YouTube manually. Today no `company-research` skill exists in this repo at all (confirmed: no `.claude/skills/company-research/` directory, no reference file, nothing under `scripts/` for this capability), and the sibling foundation ticket that builds the skill's company/website-summary core (NIC-49) is itself still in progress, not Done. FR-A3's acceptance criteria are already fairly concrete in the PRD, but two things need to be nailed down before Builder can implement anything: (1) **which recency window actually governs the video lookup** — the ticket's own description text is stale here — and (2) **the exact search mechanism and output shape**, since no retrieval approach or file/module home has been decided for this specific capability yet.

## 2. Objective

Define exactly how the `company-research` skill's YouTube-video-lookup capability behaves: what recency rule it enforces, what fields it must output on a hit, what exact fallback string it must emit on a miss, how it determines "the company" from available inputs, what search mechanism it uses (and why), how its output is represented for eventual assembly into the full brief (NIC-53's job), and where the code/reference material for this capability should live given NIC-49's current (non-Done) state.

## 3. Critical correction: ticket description is stale on the recency window

**The ticket's own description text is WRONG and must not be followed literally.** It says:

> "Note: the recency window is an OPEN QUESTION per the PRD (OQ-14) — the PRD's placeholder recommendation is 12 months but this is explicitly NOT yet confirmed/decided; do not hardcode a different window (e.g. 6 months) without validation."

This is stale. Verified directly against Linear this session:

- **NIC-31** — "OQ-14 — RESOLVED: recency window is 6 months for both video and news" — status **Canceled** in Linear's workflow sense (Linear "Canceled" is being used here as "resolved/closed out," not "rejected" — its own title and body say RESOLVED), with an explicit resolution body: *"6 months for both. The PRD's original 12-month suggestion is superseded. YouTube video: most recent relevant video within the last 6 months, otherwise 'no recent video found'. ... Nothing older is substituted in to fill a gap."*
- `docs/PRD.md` OQ-14 (line 245, 297) still shows the 12-month placeholder as "not yet confirmed" — the PRD document itself has not been updated to reflect NIC-31's resolution. This is a **documentation drift issue in the PRD**, not evidence that 12 months is still live.

**Decision for this scope doc: use 6 months, not 12.** NIC-31 is the authoritative, later, explicit resolution; the PRD text and NIC-50's own ticket description are both stale artifacts that predate it. Boss/human should be made aware the PRD's OQ-14 section and NIC-50's ticket description both need a text correction pass so future readers don't repeat this same stale-12-months mistake (flagged as an open item in §10).

## 4. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` — pipeline rules, handoff contract, Linear ticket lifecycle.
- `docs/PRD.md` — FR-A3 (line 117), US-4 (line 268), OQ-3 resolution (general web search/browsing, no new paid Apify actor, line 231), OQ-14 (lines 245, 297 — stale, see §3), Phase 3 rollout note (line 211: "Build the new `company-research` skill and attach briefs to job pages").
- `docs/PLAN.md` — confirms Phase 3 (`company-research` skill) has **not started**; NIC-42/43/45/46/47/48/56 (Phases 1/2 + LinkedIn import) are the only shipped work. No `company-research`-related script exists.
- `docs/handoffs/NIC-43-product-planner-scope-validation.md`, `docs/handoffs/NIC-56-product-planner-scope-validation.md` — style/format reference for this document, and precedent for how prior tickets handled multi-track mechanism decisions and PRD-drift flags.
- Linear: NIC-50 (this ticket, description quoted above), NIC-49 (P3-T1, state **In Progress**, not Done — scope: company/website summary, FR-A1/FR-A2), NIC-31 (OQ-14 resolution, state Canceled/Resolved, quoted above).
- Repo file search confirms: **no `.claude/skills/company-research/` directory exists**, no `company-research`-named file exists anywhere in the repo yet (scripts/, docs/, or elsewhere).

## 5. Facts, assumptions, and decisions (separated explicitly)

### 5.1 Facts
- No `company-research` skill scaffold exists yet anywhere in this repo.
- NIC-49 (the sibling ticket that would build the skill's foundational company/website-summary piece and, presumably, any shared skill scaffolding) is **In Progress, not Done** — this ticket cannot assume NIC-49's file layout or shared helpers already exist.
- NIC-31 is the authoritative, later resolution of OQ-14: **6 months**, for both video and news, nothing older substituted in.
- PRD's OQ-3 is resolved: retrieval mechanism for company research is **general web search/browsing**, explicitly **no new paid Apify actor for v1**.
- This repo's architecture has zero backend/database/hosted-service additions anywhere in scope (Notion + Claude Code skills + n8n only, per AGENTS.md/PRD).

### 5.2 Assumptions (explicit)
- Assumed: "company name" is available as an input to this capability (from the Notion card's `Company` property, populated since NIC-42), optionally supplemented by a job posting URL or the company's own website URL (once NIC-49 resolves that), for company-identity disambiguation (e.g., distinguishing "Mistral" the AI company from unrelated same-named entities).
- Assumed: "today" for the 6-month recency calculation is the date the skill is invoked/run, not the job's `selected` date or any other stored timestamp — consistent with NIC-31's plain-language resolution ("within the last 6 months").
- Assumed: this ticket produces a **self-contained, callable unit of logic** (skill reference content + a thin script/instructions Claude Code follows), not a fully wired Notion-writing pipeline — attaching the video into the actual brief/Notion page is NIC-53's job (per the ticket's brief-assembly framing referenced in the PRD's Phase 3 description), not this ticket's.

### 5.3 Decisions this scope doc makes (Product Planner judgment calls, flagged as such)
- **Recency window = 6 months** (§3) — overriding the stale ticket text.
- **Search mechanism = general web search/browsing tools** (Claude Code's built-in web search/fetch, or Hermes-equivalent `web_search`/`web_extract`), **not** a YouTube Data API integration — see §6 for full rationale.
- **File/module ownership**: given NIC-49 is not yet Done, this ticket should NOT assume a shared `.claude/skills/company-research/SKILL.md` scaffold already exists to extend. Recommend this ticket ship as a **self-contained reference/logic unit** (a documented procedure + acceptance-tested output contract) that NIC-49's eventual skill scaffold — or, if NIC-49 ships first, a section appended to it — can incorporate without rework. See §8 for the concrete recommendation and the ownership-boundary call-out.

## 6. Search mechanism decision

**Recommendation: general web search via Claude Code's built-in web search/browsing tools** (in this Hermes environment, `web_search`/`web_extract`; in plain Claude Code, `WebSearch`/`WebFetch`) — consistent with, and required by, the PRD's already-resolved OQ-3 ("general web search/browsing," "no new paid Apify actor for v1").

**Concrete approach:**
1. Query 1 (channel discovery): `"<company name> official YouTube channel"` — establishes whether the company has a findable, canonical channel and its handle/URL.
2. Query 2 (recent-content discovery): `"<company name>" (interview OR "product demo" OR culture OR announcement) site:youtube.com` — surfaces individual recent videos even without a canonical channel, or when the channel itself doesn't surface upload dates cleanly via search.
3. From returned results, extract candidate video title, channel name, and publish date (search snippets and/or the video's own page/metadata via `web_extract` on the video URL) for each candidate.
4. Filter candidates to those with a publish date within 6 months of "today" (§5.2); if the publish date cannot be determined with reasonable confidence for a candidate, treat it as **not usable** rather than guessing/assuming it's recent (no-fabrication rule).
5. Select the single most recent qualifying video (if multiple qualify, prefer the one most clearly *about* or *from* the company, e.g. published on the company's own channel or explicitly naming the company in the title, over a tangential mention).
6. If zero candidates pass the recency+relevance filter, emit the fallback string (§7) — do not fall back to an older or loosely-related video.

**Why NOT a YouTube Data API integration:** A YouTube Data API v3 integration would require registering a new Google Cloud project and a new API key — a new credential dependency of the same category the PRD's OQ-3 resolution already declined for company research generally (it explicitly ruled out a new paid Apify actor for the same reason: keep v1 on general web search/browsing, no new paid/keyed service). Introducing a new API key here would be an unstated architecture expansion beyond what OQ-3 approved, even though YouTube Data API itself has a free tier — the issue is the *new credential/dependency surface*, not cost. **This is flagged as an open question for human approval (§10), not silently assumed.** If general web search/browsing proves unreliable at finding accurate publish dates in practice (a real risk — see §9), a follow-up ticket proposing the YouTube Data API as a v2 upgrade, with its own credential-provisioning step, would be the correct way to revisit this — not something this ticket should quietly build.

**ToS/access-risk check:** General web search and fetching public, non-authenticated YouTube search-result pages and public video pages is materially different from the LinkedIn authenticated-scraping risk flagged in NIC-56 — there is no login wall, no personal account data, and no credential involved. This is the same category of access already used (or assumed) for the company-website-summary lookup in NIC-49 and for company news search elsewhere in FR-A6. **No ToS/access risk is flagged for this mechanism** beyond the general good practice of not aggressively hammering YouTube's search endpoints (a handful of searches per company/job is not a concern).

## 7. Concrete, testable acceptance criteria

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | Given a company name (and optionally a job posting URL and/or company website URL from NIC-49's output), the capability searches for a recent YouTube video about that company using general web search/browsing only (no YouTube Data API, no new Apify actor). | FR-A3, OQ-3 | Code/reference review confirms only web-search/fetch tool calls are used; no API-key-requiring call is present. |
| AC2 | **Recency rule:** a candidate video qualifies only if its publish date is within the last **6 months** of the date the skill is run ("today"). Nothing older is ever substituted in. | NIC-31 (OQ-14 resolution) — **overrides the stale 12-month text in this ticket's own description** | Given a fixed "today" and a set of candidate videos with known publish dates, videos ≤6 months old are accepted, videos >6 months old are rejected outright — verified with at least one boundary-case test (a video published exactly at/just past the 6-month mark). |
| AC3 | **On a hit:** output includes exactly three fields — **title**, **publish date**, **URL** — for the single most recent qualifying video. | FR-A3, ticket AC | Output object/markdown snippet contains all three fields, non-empty, for a known-good test company with a verifiable recent video. |
| AC4 | **On a miss** (zero qualifying candidates found): output is the exact literal string **"no recent video found"** — not a paraphrase, not an old video, not a blank/null field. | FR-A3, ticket AC, NIC-31 | Given a test company with no video activity in the last 6 months (or a fabricated/synthetic no-match scenario), output is exactly `"no recent video found"` — string-matched, not fuzzy-matched. |
| AC5 | **No fabrication:** if a candidate's publish date cannot be confidently determined, it is excluded from consideration entirely — the skill never guesses a date or presents an undated video as if it were verified-recent. | AGENTS.md hard rule, PRD NFR "Data integrity" | Review of the procedure confirms an explicit "exclude if date unconfirmed" branch, not an implicit assumption; spot-check against one video whose publish date is deliberately ambiguous in search results. |
| AC6 | **Company-identity handling:** the search query construction uses the company name as the primary identity signal, with the job URL/website URL (when available) used only for disambiguation, not as a substitute for a distinct company-name field. | US-4, ticket "Depends on P3-T1" framing | Given two same-named-but-different companies (e.g., a common company name with multiple real-world matches), the procedure documents how it would attempt disambiguation (channel-name matching against the known company website domain/handle) rather than picking the first result blindly. |
| AC7 | **Output representation:** the result (hit or miss) is expressed as a small, self-contained markdown snippet with a fixed shape, ready for a future brief-assembly step to insert verbatim — not raw tool output, not a Notion API call. | Ticket framing ("brief," US-4), ownership boundary with NIC-53 | The documented output contract (see §8.3 below) is followed exactly; no Notion write, no other skill's output format, is touched by this capability. |
| AC8 | This capability does not perform any Notion write, does not modify NIC-49's or any other skill's files, and does not require NIC-49 to be Done first to be independently testable (it can be exercised standalone with just a company name as input). | Ownership boundary (§8), AGENTS.md ("smallest working increment") | The capability can be invoked/tested in isolation, passing only a company name, without any dependency on NIC-49's unshipped code. |

## 8. Output representation, file/module layout, and ownership boundary with NIC-49

### 8.1 Ownership boundary — why this matters now
NIC-49 (P3-T1) is the ticket that builds the **new company-research skill's foundation** (company/website summary, FR-A1/FR-A2) and is still **In Progress**. NIC-50 (this ticket) is explicitly scoped as an **extension** of that skill ("Extend the `company-research` skill..."), but since the skill doesn't exist yet as a shipped artifact, NIC-50 cannot literally "extend" anything today. Two sequencing risks follow directly from this:
- If Builder starts NIC-50 before NIC-49 lands, there is no `.claude/skills/company-research/SKILL.md` (or scripts/ scaffold) to extend — Builder would either have to build scaffolding that's really NIC-49's job (scope creep, duplicated/conflicting work if NIC-49 lands differently), or block on NIC-49.
- If NIC-50 is built as a fully standalone script disconnected from whatever shape NIC-49 ships, there's rework risk reconciling the two later.

### 8.2 Recommendation: minimal standalone reference unit now, designed for a clean merge later
Given NIC-49 is not Done, **recommend NIC-50 ship as a small, self-contained reference/logic document plus one standalone script**, not full skill scaffolding:
- **Do not** create `.claude/skills/company-research/SKILL.md` in this ticket — that scaffold decision (skill frontmatter, overall SKILL.md structure, how it's invoked, what other sections like headcount/news look like) belongs to NIC-49 as the foundation ticket. NIC-50 creating it first risks conflicting with NIC-49's own scaffold choices.
- **Do** create a standalone, independently testable script — recommended path `scripts/company_research_youtube_video.py` — that takes a company name (and optional job/website URL) as input and returns the AC3/AC4 output shape (§8.3) using web-search/fetch tool calls. This mirrors this repo's established pattern of building capability-specific standalone scripts under `scripts/` (e.g., `notion_cv_attachment.py`, `notion_import_saved_jobs.py`) that are later composed together, rather than one monolithic skill file built all at once.
- **Do** write the search procedure and output contract as a documented markdown reference (this scope doc's §6/§7/§8.3 already serves as that source of truth; Builder should also add a short `docs/ARCHITECTURE.md` "NIC-50" section per repo convention) so that whenever NIC-49 lands its `SKILL.md` scaffold, incorporating this capability as one of its documented steps/sections is a copy-in of an already-tested contract, not new design work.
- **Flag explicitly to Boss/Builder:** once NIC-49 ships its skill scaffold, a small **fast-follow integration ticket** (wiring `scripts/company_research_youtube_video.py`'s logic into the actual `SKILL.md` flow) may be needed — this scope doc does not assume that wiring happens automatically as a side effect of either ticket.

### 8.3 Output contract (markdown snippet, ready for NIC-53 assembly)

On a hit:
```markdown
**Recent YouTube video:** [<title>](<url>) — <channel name>, published <publish date, e.g. 2026-05-14>
```

On a miss:
```markdown
**Recent YouTube video:** no recent video found
```

This snippet-per-field pattern (label in bold, single line, explicit "no recent video found" fallback) is chosen to match the PRD's FR-A6 news-item style ("dated, sourced" one-liners) and to be trivially insertable into the "🔍 Company Research Brief" placeholder section NIC-43 already created in the per-job Notion page template — the eventual brief-assembly ticket (referenced as NIC-53 in the task context) can concatenate this snippet with the website-summary (NIC-49), headcount, and news snippets without any format translation.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| General web search may not reliably surface accurate publish dates for YouTube videos (search snippets sometimes show relative dates like "2 months ago" tied to crawl time, not upload time, or omit dates entirely). | Medium — could cause false negatives (rejecting a genuinely recent video because its date couldn't be confirmed) or, worse, false positives if a stale relative-date string is misread. | AC5 mandates excluding any candidate with an unconfirmed date rather than guessing — biases toward under-reporting (more "no recent video found" outcomes) rather than fabricating recency, consistent with the no-fabrication hard rule. Recommend Builder fetch the actual video page (via `web_extract`/`WebFetch`) to read structured upload-date metadata when available, rather than trusting search-snippet text alone. |
| Small/private companies may have no YouTube presence at all, making "no recent video found" the common-case output rather than the edge case. | Low | This is an explicitly valid, expected output per FR-A3/AC4 — not a defect. No mitigation needed beyond ensuring the fallback string is exact and doesn't read as an error. |
| Company-identity ambiguity (common company names) could surface an unrelated company's video as if it were about the target company. | Medium | AC6's disambiguation approach (matching against known website domain/handle when available) mitigates but does not eliminate this — flagged as a residual risk Builder/QA should spot-check with at least one ambiguous-name test case. |
| Sequencing risk with NIC-49 (§8.1) — building this before the skill scaffold exists could require rework once NIC-49 ships. | Medium | §8.2's standalone-script recommendation minimizes rework by keeping this ticket's deliverable a clean, independently-testable unit with a stable output contract, deferring scaffold integration to a flagged fast-follow rather than guessing at NIC-49's eventual shape. |
| PRD OQ-14 text and this ticket's own description both still show the stale 12-month figure, and could mislead a future reader (or a differently-briefed agent) into re-litigating a settled decision. | Low–Medium | Flagged explicitly in §3 and §10; recommend a documentation fix (not a re-decision) to `docs/PRD.md` OQ-14 and, if editable, a correction note on NIC-50's Linear description, so this doesn't recur on a future related ticket (e.g., the news-recency capability under FR-A6, which shares the same NIC-31 resolution). |

## 10. Open questions / risks flagged for Boss or the human

- **OQ-1 (not blocking, documentation hygiene):** `docs/PRD.md`'s OQ-14 entry (lines 245, 297) still reads as "not yet confirmed... 12 months placeholder," which is stale given NIC-31's resolution. Recommend a follow-up documentation-only edit to the PRD marking OQ-14 **[RESOLVED — 6 months, see NIC-31]**, mirroring how other resolved OQs (OQ-1, OQ-2, OQ-3, etc.) are already marked in that same file. Not blocking this ticket's build, since this scope doc already establishes 6 months as authoritative for Builder.
- **OQ-2 (human approval needed only if pursued):** Should a future v2 of this capability use the YouTube Data API for more reliable publish-date metadata, accepting a new Google Cloud API-key credential dependency? **Not recommended for this ticket** (§6) — general web search/browsing satisfies OQ-3's existing architecture decision. Flagging this explicitly so it is a conscious, separately-approved future choice if search-based date accuracy proves insufficient in practice (§9 risk), not something silently introduced later.
- **OQ-3 (not blocking, sequencing):** Should Builder start NIC-50 now as a standalone script (§8.2 recommendation) or should Boss sequence it to start only after NIC-49 ships its skill scaffold? This scope doc recommends proceeding now as a standalone, independently-testable unit (AC8) to avoid idling Builder capacity, with the fast-follow integration ticket (§8.2) absorbing the wiring cost later — but flags this as a sequencing call Boss may want to confirm given NIC-49 is the stated dependency in the ticket's own "Depends on" field.
- **No blockers to starting Builder work** on the standalone-script scope recommended in §8.2, using the 6-month recency rule (§3) and the acceptance criteria in §7.

## 11. Effort estimate

**S — approximately 2–2.5 hours.** Reasoning: this is a single, narrow capability (one search-and-filter procedure with a fixed 3-field/1-fallback-string output contract) with no Notion writes, no file uploads, no schema changes, and no new external credential (per the recommended mechanism) — smaller than NIC-56 (which had card-creation + dedup logic) and comparable to or slightly smaller than NIC-48 (naming-convention helper). Breakdown: search-query and date-filtering logic implementation (~45–60 min), recency-boundary and no-fabrication edge-case handling (~30 min), output-contract formatting (~15 min), verification against 2–3 real test companies (one with a recent video, one with none, one ambiguous-name case) (~30–45 min), `docs/ARCHITECTURE.md` documentation (~15–20 min).

## 12. Recommended next action — handoff to Builder

1. Implement a standalone script `scripts/company_research_youtube_video.py` (naming at Builder's discretion, following the `notion_*.py`/`render_*.py` convention already in `scripts/`) that: accepts a company name (required) and optional job-URL/website-URL for disambiguation; performs the two-query web-search procedure in §6; filters candidates to the 6-month recency window (§3, AC2) with unconfirmed-date exclusion (AC5); selects the single best qualifying candidate; and emits the exact markdown snippet contract in §8.3 (hit or the literal `"no recent video found"` fallback, AC3/AC4).
2. Verify against at least 2–3 real companies (recommend testing with one company known to post YouTube content regularly, one small/private company likely to have none, and one company with an ambiguous/common name) — capture the actual search queries run, the candidate videos considered and why each was accepted/rejected, and the final output snippet, as evidence (mirroring the evidence-capture discipline established in NIC-43/46/47/48/56).
3. Do **not** build a YouTube Data API integration (§6) — flag to Boss/human if search-based date accuracy proves insufficient in testing, per OQ-2 (§10), rather than silently adding it.
4. Do **not** create `.claude/skills/company-research/SKILL.md` in this ticket (§8.1/§8.2) — that scaffold is NIC-49's responsibility; this ticket's script is designed to be incorporated into that scaffold later via a flagged fast-follow integration step.
5. Document the design decision, search procedure, and full AC1–AC8 evidence trail in `docs/ARCHITECTURE.md` (new "NIC-50" section, following the established per-ticket section format), and add a `docs/PLAN.md` entry.
6. Optionally (non-blocking, OQ-1): flag to Boss that `docs/PRD.md`'s OQ-14 text should be corrected to reflect NIC-31's resolution, since it currently still reads as unresolved/12-months.
7. Hand off to QA Reviewer with evidence: the exact search queries and tool calls made, the candidate videos considered per test company (with accept/reject reasoning tied to the 6-month rule), and the final output snippets for each test case.
