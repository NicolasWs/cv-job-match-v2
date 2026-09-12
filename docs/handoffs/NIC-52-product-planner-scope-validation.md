# NIC-52 — Product Planner Scope Validation

**Ticket:** NIC-52 — "P3-T4 — company-research skill: significant recent news"
**Traces to:** FR-A6, US-4, PRD Section 6.1 (company-research skill), PRD Section 11 Risks ("significant news" row), OQ-14 (RESOLVED, NIC-31)
**Depends on:** NIC-49 — P3-T1 — New `company-research` skill: company/website summary (parallel sibling ticket, not scoped here)
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-12
**Role boundary respected:** no code/skill implementation performed; this is scope definition only. No web search against any real company was executed as part of this scoping pass (nothing to fabricate or misreport — this ticket only defines the mechanism Builder must follow).

---

## 1. Problem restatement

Today, nothing in either repo (`cv-job-match` v1 or `cv-job-match-v2`) surfaces "is anything significant happening at this company right now" before Nicolas applies or interviews. The v1 `find-opportunities` skill's Company Radar only records an application *angle* and a *CV variant* — no external signal about funding, leadership change, restructuring, or expansion. The v1 `write-outreach`/`run-my-week` skills reference a `company-intel` input that has never existed as a real skill (confirmed gap, PRD Section 2.2/11). This ticket is the "recent news" slice of the new `company-research` skill (PRD Section 6.1): a bounded, sourced, dated list of significant company news connected to the job opportunity, or an explicit "none found" — never a fabricated or generic item.

## 2. Goal

Give Nicolas, for any job in `selected` status or later, a maximum of 3 significant-news items about the target company from the last 6 months, each dated, sourced, and explicitly tied to why it matters for *this* application — with "no significant news found" as an equally valid, non-fabricated output. This must be buildable as a Claude Code skill procedure (a `SKILL.md` step using the model's native web-search capability), never a bespoke scraper, dedicated news API, or paid Apify actor, consistent with PRD Section 6.1's "general web search/browsing, no new paid Apify actor for v1" (OQ-3, RESOLVED).

## 3. Facts, assumptions, and findings (separated explicitly)

### 3.1 Facts (verified this session)
- **No `company-research` skill file exists yet** in `/home/nicow/cv-job-match/.claude/skills/` (confirmed: directory search for `company-research` returned zero files). This ticket's Builder may find the file already created by NIC-49's Builder, or may find nothing — both are live possibilities since NIC-49 and NIC-52 run as parallel sibling pipelines with no shared state (flagged as a coordination risk, §7).
- **The 6-month recency window is already resolved**, not an open question: Linear ticket NIC-31 ("OQ-14 — RESOLVED: recency window is 6 months for both video and news") states explicitly: *"6 months for both. The PRD's original 12-month suggestion is superseded... News: 1–3 significant items from the last 6 months, each dated and sourced. Nothing older is substituted in to fill a gap."* This scope doc uses 6 months as authoritative and treats the 12-month figure in `docs/ARCHITECTURE.md` (~line 159, NIC-43's per-job page-template placeholder callout text) as stale/pre-dating this resolution — that comment is not itself a requirement, only leftover placeholder copy from before NIC-31 shipped, and it is not being corrected as part of this ticket (out of scope, see §5, but flagged as a Builder/Boss housekeeping note in §9).
- **PRD FR-A6's own acceptance criteria** ("1–3 news items max, each with a one-line 'why this matters for this application' note, dated, sourced") and **PRD Section 11's Risks table** ("Allow explicit 'no significant news found' as a valid output, consistent with the existing 'never fabricate' rule") are both already precise enough to build from directly — this scope doc's job is to make them *mechanically* concrete (exact search approach, exact significance filter, exact recency-cutoff computation, exact output string), not to re-litigate them.
- **This is a skill-procedure deliverable, not a script.** Every existing sibling skill in `/home/nicow/cv-job-match/.claude/skills/` (`find-opportunities`, `cv-match`, `write-outreach`, `interview-prep`, `run-my-week`, `kanban-status`) is a single `SKILL.md` markdown file describing a procedure for the Claude Code agent to follow, using its own native tools (web search/fetch, file read/write) — none of them are Python scripts invoked by a runner. `company-research` (NIC-49/50/51/52) follows the same pattern: this ticket's Builder deliverable is a **markdown section/step inside a `SKILL.md` file**, not a new script.
- **PRD Section 6.1's news wording**: "significant recent news connected to the job/hiring context (e.g., funding round, expansion, leadership change, product launch)." FR-A6 adds "restructuring" to that example list. This scope doc treats both lists as the same non-exhaustive category set (§4 below formalizes it).

### 3.2 Assumptions (explicit, not independently verified)
- Assumed: "connected to the job opportunity" means *company-wide* significant news (funding, leadership, restructuring, expansion, product launches), not news specifically about the exact team/department/country Nicolas is applying to — the PRD's own example list (funding round, expansion, leadership change, product launch) is generically company-level, not role-specific. Flagged as OQ-1 (§8) since Builder should not silently narrow or widen this without a cheap confirmation.
- Assumed: the "why this matters for this application" note is a Product-Planner-defined *field*, not a fixed template sentence — Builder/the skill should judge relevance per item (e.g., "recent Series C signals fast headcount growth in Product — expect this team to be scaling, a good interview talking point" vs. a generic "this shows the company is active").
- Assumed: web search tooling available to the Claude Code session running this skill is the standard built-in web-search/fetch capability (the same mechanism implied by PRD OQ-3's resolution: "general web search/browsing"), not a specific named MCP tool this scope doc can hardcode — Builder should use whatever web-search/fetch tool is available in the Claude Code environment at runtime, consistent with how no other sibling skill in the repo hardcodes a specific search tool name either.

### 3.3 Decisions this scope doc makes (Product Planner judgment calls, flagged as such)
- **"Significant" is defined by category, not by vague editorial judgment alone** (§4) — a closed-ish list of category types with concrete trigger examples, so the skill has an objective filter rather than "use your judgement," which is the actual mechanism gap in FR-A6's current wording.
- **The recency cutoff is computed at brief-generation time** (today − 6 calendar months), not at job-selection time or hardcoded to a past date — this matters because a brief regenerated later (e.g., re-run before an interview weeks after the job was selected) must use a fresh cutoff, not the cutoff from when the card was created.
- **The output contract (headline / date / source URL / why-it-matters / max 3 items / explicit none-found string) is specified exactly** (§6) so QA Reviewer has an unambiguous, testable target and Builder does not need to invent format decisions PRD.md leaves implicit.

## 4. What qualifies as "significant" news (concrete filter)

A news item is in-scope only if it fits one of these categories **and** is about the specific company being researched (not the industry in general, not a competitor, not a vague market trend piece):

| Category | Include (examples) | Exclude (examples) |
|---|---|---|
| Funding / financial event | Funding round (seed/Series A-D+), acquisition of the company, the company acquiring another company, IPO filing/completion, major investment announcement | Routine investor-relations boilerplate with no new dollar figure or milestone |
| Expansion | New office/market/country launch, publicly announced major hiring wave, entering a new product line/vertical | A single new job posting (that's not "news", that's the job board itself) |
| Leadership change | New CEO/C-suite hire or departure, board changes, founder transition | A LinkedIn post congratulating an internal promotion with no press coverage |
| Restructuring | Layoffs, reorg announcement, department closure/consolidation, leadership departure tied to a strategy shift | Normal attrition, individual employee departures |
| Product launch / major partnership | A new flagship product/feature launch with press coverage, a strategic partnership announcement | Minor feature updates, changelog entries, routine marketing content |

**Explicitly excluded regardless of category:** industry awards/rankings, generic "best places to work" listicles, sponsored content/press-release mills with no independent verification, opinion/analyst pieces that don't report a specific event, and anything the skill cannot find a specific publish date for (see §6 recency rule).

## 5. Scope

### In scope for this ticket
1. A concrete search-and-filter procedure (§6) for the "recent news" component, written as a step/section inside the `company-research` skill's `SKILL.md`.
2. The exact per-item output schema and the exact "no significant news found" fallback string (§6).
3. The exact 6-month recency-cutoff computation rule (§6).
4. Coordination guidance for Builder on the shared-file risk with NIC-49 (§7, §9).

### Explicitly out of scope for this ticket
- The company/website summary, YouTube video, or open-position-count components of `company-research` — those are NIC-49/50/51's scope, not redefined or touched here.
- Assembling all four components into one brief and attaching it to the Notion job page — that is NIC-53's scope (depends on this ticket and its three siblings all landing first).
- Correcting the stale "12-month" placeholder text in `docs/ARCHITECTURE.md`'s NIC-43 section — flagged as a housekeeping note (§9) but not blocking and not this ticket's deliverable; NIC-43's placeholder text was pre-OQ-14 and describes what a *future* skill will do, it does not implement or gate anything today.
- Any Notion API call, page creation, or attachment — this ticket produces a skill procedure only; wiring the resulting content onto a Notion page is FR-A7/NIC-53's job.
- Any new paid data source (Apify actor, dedicated news API, LinkedIn scraping) — explicitly rejected per PRD Section 6.1/OQ-3.
- Building or modifying `find-opportunities`, `write-outreach`, `interview-prep`, or `run-my-week` — those are only *consumers* of `company-research`'s eventual output (via the `company-intel` gap), not touched by this ticket.

## 6. Functional requirements (concrete, testable)

**FR-52.1 — Search mechanism.** The skill uses the Claude Code session's native web-search/fetch capability (general web search/browsing, per PRD OQ-3 resolution — no new paid Apify actor, no dedicated news API, no LinkedIn scraping). Recommended query pattern: `"{company name}" (funding OR acquisition OR layoffs OR restructuring OR "new CEO" OR expansion OR "product launch") {current year}`, run at least once; if the company name is ambiguous (common word, multiple companies share it), add a disambiguating term from the job posting (industry, HQ city) to the query.

**FR-52.2 — Significance filter.** Only items matching one of the five categories in §4 qualify. The skill must be able to state, for each candidate item it considers, which category it matched — this is an internal judgment step, not part of the final output, but Builder's implementation should make this filter step explicit/traceable in the skill's procedure text (so a future reviewer can see *why* an item was kept or dropped), not an implicit one-line judgment call.

**FR-52.3 — Recency cutoff.** Compute the cutoff as "today's date minus 6 calendar months" at the moment the brief is generated (not at job-selection time, not hardcoded). An item is in-scope only if its own publish date is on or after that cutoff. If a candidate item has no discoverable, specific publish date, it is discarded, not included with a guessed or approximate date.

**FR-52.4 — Per-item output schema.** Each included news item must render as exactly these four fields, in this order:
```
- **Headline:** <verbatim or lightly-trimmed source headline, not embellished>
- **Date:** <YYYY-MM-DD, the source's own publish date>
- **Source:** <full article URL>
- **Why it matters for this application:** <one sentence, specific to this company/role, not generic filler>
```

**FR-52.5 — Item count.** Minimum 0, maximum 3 items. If more than 3 qualifying items are found, keep the 3 most significant (funding/leadership/restructuring generally outrank a product launch or minor expansion, but use judgment on genuine impact, not just category order) and do not list the rest.

**FR-52.6 — Explicit "no significant news found" case.** When zero qualifying items exist after applying §4's filter and the 6-month cutoff, the skill's output for this section must be **exactly**:
```
No significant news found for {Company} in the last 6 months.
```
(with `{Company}` substituted for the actual company name) — not silently omitted, not replaced by an old/irrelevant item, not phrased as an apology or hedge. This satisfies FR-A6/PRD Section 11's "never fabricate" risk mitigation.

**FR-52.7 — Never substitute stale items to fill the quota.** If only 1 or 2 qualifying items exist, output only those 1 or 2 — do not pad to 3 with a lower-quality or borderline item just to hit the max. "Fewer, well-qualified items" beats "3 items to look complete."

**FR-52.8 — Retrieval date stamp.** The overall news section (not each item — items already carry their own publish date per FR-52.4) states the date the search was run, e.g. `_Retrieved: {today's date}_`, consistent with the PRD's Non-Functional "Recency" requirement (Section 8: "Company research data (news, headcount) should show a retrieval date so staleness is visible").

## 7. Non-functional requirements

- **No fabrication (hard constraint):** every item must have a real, checkable source URL; the skill must never invent a headline, date, or "why it matters" rationale not grounded in the actual article content.
- **Source quality bar:** prefer primary sources (the company's own newsroom/press page, a named mainstream or trade-press outlet) over content-farm aggregators or unverified social posts; if only a low-quality source can be found for an otherwise-qualifying event, include it but do not treat a single unverified tweet/LinkedIn post as sufficient sourcing on its own.
- **Degrades gracefully for small/private companies:** many of Nicolas's target companies (per PRD Section 3, AI/Data PM roles, Paris market) may be small, private, or have thin public news coverage — FR-52.6's "no significant news found" must be a first-class, unremarkable output for this segment, not treated as a skill failure.
- **Consistency with sibling FR-A3 (video) pattern:** this news component should read naturally alongside NIC-50's video component and NIC-49's summary component in the eventual assembled brief (NIC-53) — same "state clearly what wasn't found" tone, same dated/sourced discipline — but this ticket does not implement or verify that combined rendering (NIC-53's job).
- **No network calls beyond web search/fetch:** consistent with PRD Section 6.1, no Notion API calls, no LinkedIn access, no paid actor invocation from this skill step.

## 8. Acceptance criteria (numbered, testable — more concrete than the Linear ticket's own AC)

| # | Criterion | Testable check |
|---|---|---|
| AC1 | Given a company with genuine recent news matching one of the five §4 categories within the last 6 months, the skill's output includes 1–3 items, each with all four FR-52.4 fields populated and non-empty. | Run the skill against a real company known to have recent funding/leadership news (Builder's choice of verification target); confirm each returned item has Headline, Date, Source, and Why-it-matters, none blank. |
| AC2 | No output item has a publish date older than "today − 6 calendar months" at generation time. | Inspect the Date field of every returned item; compute the cutoff independently; confirm all dates ≥ cutoff. |
| AC3 | No more than 3 items are ever returned, even if more qualifying items exist. | Run against a company with heavy recent press coverage (e.g., a large company with several qualifying events in the window); confirm output caps at exactly 3, prioritized by significance. |
| AC4 | Given a company with no discoverable significant news in the last 6 months (e.g., a small/quiet private company), the skill outputs exactly the FR-52.6 string, substituting the real company name, and does not fabricate or substitute an older/irrelevant item. | Run against a deliberately quiet/small target; confirm the literal output string and confirm no item-shaped content appears in its place. |
| AC5 | Every included item's category (per §4's five-category filter) can be identified by re-reading the skill's own procedure text — i.e., the significance filter is written into the skill as an explicit, followable step, not left as an implicit "use good judgment" instruction. | Read the shipped `SKILL.md` section; confirm it contains the five-category table (or equivalent enumeration) and the recency-cutoff computation instruction, not just a one-line "find significant news" prompt. |
| AC6 | The skill never queries `linkedin.com`, a paid Apify actor, or any dedicated news API — only general web search/browsing. | Code/prose review of the shipped `SKILL.md` section confirms no such tool/actor is named or required. |
| AC7 | The retrieval date is stated once per news section, distinct from each item's own publish date. | Confirm output includes a `Retrieved: <date>` line separate from per-item `Date:` fields. |
| AC8 | If fewer than 3 qualifying items exist (1 or 2), the skill does not pad the list with a non-qualifying item to reach 3. | Run against a company with exactly 1–2 genuinely qualifying items; confirm output contains only those, not 3. |

## 9. Coordination risk: NIC-49/NIC-52 parallel siblings, shared file, no shared state

**This is the single most important operational risk for this ticket** and is called out explicitly per the task's instructions.

- NIC-49 (company/website summary) and NIC-52 (this ticket, recent news) are both building pieces of the *same* file: `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md`. They are dispatched as separate Linear tickets/Builder runs with no shared state or locking.
- **Two possible states when this ticket's Builder starts work:**
  1. NIC-49's Builder has not yet created the file → this ticket's Builder should create `company-research/SKILL.md` from scratch, including this ticket's "recent news" section, plus a minimal skeleton for the other sections (summary/video/headcount) marked as pending/placeholder — so NIC-49/50/51's Builders have a consistent file to extend into, mirroring the "avoid clobbering a sibling's future edit" spirit of NIC-43's placeholder-callout pattern.
  2. NIC-49's Builder has already created the file (with a company-summary section) → this ticket's Builder should **append** a new "Recent news" section without altering NIC-49's existing content, and should read the existing file first to match its established heading/style conventions rather than introducing a divergent format.
- **Risk if unmanaged:** whichever Builder runs second could silently overwrite the first Builder's work if it doesn't check for the file's existence and read it first, or the two sections could end up with inconsistent tone/structure/heading levels since neither Builder can see the other's ticket.
- **Mitigation (Builder-level, not blocking):** Builder MUST `cat`/read the target file's current contents before writing, use additive edits (append a clearly-delimited "## Recent Company News" section, or equivalent heading matching whatever convention already exists in the file) rather than a full-file rewrite, and note in its Linear/handoff comment whether it created the file fresh or appended to an existing one.
- **Recommendation for Boss:** if operationally feasible, sequence NIC-49 and NIC-52's Builder dispatches (even a few minutes apart) rather than firing both simultaneously, to reduce (not eliminate) the race window; this scope doc does not block on it since Builder-level defensive read-before-write handles the substantive risk either way.

## 10. Other risks and assumptions

| Risk | Impact | Mitigation |
|---|---|---|
| Web search/browsing may return sparse or no results for small/private companies (a large share of Nicolas's AI/Data PM target list per PRD Section 3). | Medium | FR-52.6's explicit "no significant news found" output is a first-class, expected outcome for this segment — not a failure mode to work around by lowering the significance bar. |
| Search-tool rate limits or transient failures could interrupt the news-lookup step mid-brief. | Low–Medium | Skill should retry once, then fall back to reporting "unable to complete news search this run" (a distinct message from FR-52.6's "none found," since one is a search failure and the other is a genuine negative result) — flagged as an implementation detail for Builder, not a blocking scope decision. |
| Source reliability varies widely on the open web; a content-farm or SEO-spam site could surface a plausible-looking but low-quality "news" item. | Medium | §7's source-quality bar (prefer primary/mainstream/trade press) mitigates but does not eliminate this — Builder should build a lightweight quality heuristic into the skill's procedure text (e.g., prefer sources with a clear byline/publication and an actual publish date) rather than accepting every search hit uncritically. |
| The stale 12-month reference in `docs/ARCHITECTURE.md` (NIC-43 section, ~line 159) could confuse a future reader who doesn't know it predates OQ-14's resolution. | Low | Not this ticket's fix (out of scope, §5) — flagged in §9/here so Boss or a future housekeeping ticket can correct the placeholder text to say 6 months once `company-research` actually ships and that section is naturally revisited. |
| NIC-49/NIC-52 coordination (shared file, no shared state) — see §9 for full detail. | Medium–High | Builder-level read-before-write discipline (§9); optional Boss-level dispatch sequencing. |

## 11. Open questions

- **OQ-1 (not blocking, recommend Boss confirm with Nicolas if convenient, otherwise proceed on this assumption):** Is "connected to the job opportunity" satisfied by company-wide significant news (funding, leadership, restructuring, expansion, product launches), or does Nicolas want news filtered further to the specific team/department/geography he's applying to? This scope doc assumes company-wide is sufficient, matching the PRD's own example list, which is entirely company-level, not role-specific.
- **OQ-2 (not blocking):** Should a search-tool failure (rate limit, no connectivity) be reported differently from a genuine "no news found" result, so Nicolas can tell the difference between "nothing happening at this company" and "the search didn't run properly"? Recommend Builder implement this distinction (§10) as good practice, but it is not a hard AC for this ticket since PRD/FR-A6 do not explicitly require it.
- **OQ-3 (not blocking, informational):** Should the stale 12-month placeholder text in `docs/ARCHITECTURE.md`'s NIC-43 section be corrected to 6 months as a small housekeeping edit once `company-research` ships? Recommend yes, as a one-line follow-up whenever a Builder next touches that section (e.g., naturally during NIC-49/50/51/52's own documentation step), not a blocking prerequisite for this ticket.
- **No blockers to starting Builder work.** This ticket's scope, output contract, and coordination guidance (§9) are sufficient to begin implementation; the only genuine open items (OQ-1–3) are refinements, not gating decisions.

## 12. Go/no-go recommendation

**GO.** Builder should implement the "recent news" section of the `company-research` skill exactly per §6's output contract and §4's significance filter, following §9's defensive read-before-write discipline given the NIC-49 coordination risk. This is a small, additive, skill-procedure-only change (no code, no Notion calls, no new infrastructure) that can be verified by running the skill against 1–2 real companies (one with genuine recent news, one quiet/small one to confirm the "none found" path) before handing off to QA Reviewer.

---

## HANDOFF TO BUILDER

**Objective:** Implement the "recent news" component of the new `company-research` Claude Code skill in the v1 repo (`/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md`), per the exact output contract, significance filter, and recency-cutoff rule defined in this document.

**Context and relevant files:**
- v1 repo: `/home/nicow/cv-job-match` (skill lives here, NOT in `cv-job-match-v2`).
- Target file: `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` — **check whether this file already exists (likely from NIC-49) before writing; read it first if so** (§9).
- Sibling skill examples for style/structure conventions: `.claude/skills/find-opportunities/SKILL.md`, `.claude/skills/interview-prep/SKILL.md` (both in the same repo).
- This document (`docs/handoffs/NIC-52-product-planner-scope-validation.md`, in `cv-job-match-v2`) for full rationale, the five-category significance filter (§4), the exact output schema (§6), and the coordination protocol (§9).
- PRD reference: `docs/PRD.md` (in `cv-job-match-v2`) Section 6.1, FR-A6, Section 11 Risks, Section 8 NFR Recency.
- Linear: NIC-31 (OQ-14 RESOLVED — 6-month window, authoritative over the stale 12-month text in `docs/ARCHITECTURE.md`'s NIC-43 section).

**Constraints:**
- No new paid Apify actor, no dedicated news API, no LinkedIn access — general web search/browsing only (PRD Section 6.1/OQ-3).
- Never fabricate a headline, date, source, or rationale — every item must be independently checkable via its Source URL.
- Max 3 items; never pad to reach 3; "no significant news found" (exact wording, FR-52.6) is a first-class valid output.
- 6-month recency cutoff computed at brief-generation time, not hardcoded to any specific date.
- If `company-research/SKILL.md` already exists (NIC-49), append additively; do not overwrite or restructure NIC-49's existing content.
- No Notion API calls, no card creation/attachment — that is NIC-53's scope.
- No deployment, no destructive operation, no secret exposure, no third-party contact beyond ordinary web search/fetch.

**Acceptance criteria:** AC1–AC8 in §8 above.

**Files likely to touch:**
- `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` (create or append) — **in the v1 repo**, not `cv-job-match-v2`.
- `docs/ARCHITECTURE.md` (this repo, `cv-job-match-v2`) — new "NIC-52" section documenting the design decision and verification evidence, per established repo pattern (see NIC-42/43/46/47/48/56 precedent).
- `docs/PLAN.md` (this repo) — new NIC-52 entry.

**Recommended next action:** Builder checks for the existing `company-research/SKILL.md` file, reads it if present, implements the "Recent news" section per §4/§6 of this document, verifies against at least one real company with genuine recent news and one quiet/small company (confirming the "no significant news found" path), documents evidence in `docs/ARCHITECTURE.md`/`docs/PLAN.md`, and hands off to QA Reviewer. Flag in the handoff comment whether the skill file was created fresh or appended to NIC-49's existing work, per §9's coordination note.
