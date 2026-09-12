# NIC-51 (P3-T3) — Product Planner Scope Validation

**Ticket:** NIC-51 — "P3-T3 — company-research skill: open-position counts (France + HQ country)"
**Traces to:** FR-A4, FR-A5, US-4
**Depends on (per ticket text):** P3-T1 — NIC-49, "New company-research skill: company/website summary"
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-12
**Role boundary respected:** no code/skill implementation performed; this is scope definition only. No web search, browser automation, or LinkedIn access was performed during this investigation. No skill files were created. No Linear ticket other than NIC-51 itself was mutated (NIC-49/50/52/53 were only read, via `issue` query, to resolve the dependency question in §4).

---

## 1. Problem restatement

FR-A4/FR-A5 require the `company-research` brief to report the count of open positions a company has in France, and — when different — in the company's headquarters country, each with a numeric count, a named source, and a retrieval date (counts change over time, so a stale unsourced number is worse than no number). This is one of five planned sections of the overall brief (company summary [NIC-49], YouTube video [NIC-50], open-position counts [this ticket, NIC-51], recent news [NIC-52], and the Notion-attach/`company-intel` wiring [NIC-53]). NIC-51's own Linear description names NIC-49 as a dependency, which raises a sequencing question this document must resolve explicitly (§4) before any other scoping proceeds, since the `company-research` skill does not exist anywhere in the repo yet.

## 2. Objective

Define (scope only, no code):
1. Whether NIC-51 must wait for NIC-49 to ship, or can create the skill scaffold itself (§4 — the load-bearing decision for this whole document).
2. The exact data source(s) and retrieval method for the two counts, consistent with PRD OQ-3 (general web search/browsing, no new paid Apify actor) and this repo's established no-LinkedIn-automation precedent (NIC-56).
3. How "France" vs. "HQ country" is determined precisely enough for Builder to implement without guessing.
4. Explicit graceful-degradation behavior when a precise count cannot be found, consistent with the PRD's "never fabricate" hard rule.
5. A concrete output contract (data shape) that NIC-53's future Notion-attach step can consume without re-negotiating this ticket's design.
6. Testable acceptance criteria extending NIC-51's own two ticket-level ACs into Builder-verifiable checks.

## 3. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` — handoff contract, Linear ticket lifecycle/state machine, forbidden operations (no third-party contact / no destructive ops without human approval — relevant to the LinkedIn-ToS question in §5.1), the explicit prohibition on proposing a bespoke web app or new backend.
- `docs/PRD.md` — FR-A1–A7 (full company-research brief spec), US-4, Section 6.1 (`company-research` in-scope description), OQ-3 (resolved: general web search/browsing, no new paid Apify actor), OQ-7 (resolved: one new `company-research` skill, also closes the `company-intel` gap), the Risks table row on open-position-count data being "often inconsistent... stale or wrong" (mitigation: always cite source + retrieval date).
- `docs/PLAN.md` — Phase 3 = `company-research` skill + brief attachment; confirms Phase 3 is the current active phase and no company-research work has landed yet.
- `docs/ARCHITECTURE.md` — the per-job Notion page template's "Company Research Brief" section is currently a placeholder `callout` block explicitly marked "Pending — populated by the `company-research` skill (Phase 3, not yet built)" — confirms, independently of the Linear read below, that no company-research output exists anywhere in Notion either.
- `docs/handoffs/NIC-44-`, `NIC-56-`, `NIC-62-product-planner-scope-validation.md` — read for house style/structure and for established precedents this document reuses: NIC-44's "new standalone skill in the v1 repo, `.claude/skills/<name>/SKILL.md`" pattern (used for `kanban-status`); NIC-56's LinkedIn/ToS risk-flagging pattern and its explicit "no browser automation against linkedin.com, no credentialed access, no session cookies" constraint, which this document applies to open-position counting for the same reasons.
- `/home/nicow/cv-job-match/.claude/skills/kanban-status/SKILL.md` — read in full as the concrete precedent for a small, standalone, additive skill added directly to the v1 repo's `.claude/skills/` directory without waiting on a "foundation" ticket to physically merge first (NIC-44 had no such dependency, but the directory-creation pattern — frontmatter + a single focused Markdown procedure file — is the template this document recommends reusing for the `company-research` scaffold).
- `/home/nicow/cv-job-match/.claude/skills/` directory listing (confirmed via file search): `cv-match`, `find-opportunities`, `interview-prep`, `kanban-status`, `run-my-week`, `write-outreach`. **No `company-research` directory exists.**
- `/home/nicow/cv-job-match/.claude/skills/run-my-week/SKILL.md` and `write-outreach/SKILL.md` — read for the `company-intel` references PRD OQ-7 says `company-research` must fill: `run-my-week` calls it "company-intel (light pass). Skip if an `intel-<company>.md` newer than 30 days exists"; `write-outreach` says "Company notes — `company-intel` output if available, else anything known" and, on refinement plateau, suggests "running `company-intel` and re-looping once with its output." No `company-intel/SKILL.md` file exists — confirms the PRD's characterization of this as a previously-undocumented gap, not an existing skill this ticket must integrate with today (that integration is explicitly NIC-53's job, not this ticket's).
- Linear (read-only `issue` query, this session): confirmed live state/labels/descriptions for NIC-49 (Todo, label `Boss`), NIC-50 (Todo, label `Boss`), NIC-51 (In Progress, label `Boss` — this ticket), NIC-52 (In Progress, label `Boss`), NIC-53 (Todo, no label). NIC-53's own description explicitly lists its dependency as "P3-T1..P3-T4" (i.e., NIC-49, 50, 51, 52 all — not just NIC-49), confirming NIC-53 is the ticket that waits for the full set, not NIC-51.

## 4. Dependency resolution: NIC-49 is Todo — does NIC-51 wait, or scaffold now? (load-bearing decision)

**Fact:** NIC-51's own Linear description states "Depends on: P3-T1 — New company-research skill: company/website summary" (NIC-49). Live Linear state (confirmed this session): NIC-49 is **Todo**, not started — no `company-research` skill directory exists anywhere in either repo.

**Decision: Option (a) — Builder creates the `company-research` skill scaffold now, in this ticket, containing only the open-positions-count capability, structured so NIC-49/50/52's future work can add sibling sections without conflict. NIC-51 does NOT block on NIC-49 shipping first.**

Reasoning:
- **NIC-53, not NIC-51, is the ticket that actually needs all four sibling tickets done.** Confirmed directly from NIC-53's own Linear description (§3): its dependency line reads "P1-T2 ... P3-T1 ... P3-T2 ... P3-T3 ... P3-T4" — i.e. NIC-53 (attach-to-Notion + wire as `company-intel` source) is the aggregation point that needs the *complete* brief. NIC-51's dependency on "P3-T1" most plausibly describes a **narrative/reading-order convenience** in the ticket description (each of NIC-50/51/52 says "Depends on: P3-T1" identically, suggesting a templated description, not four independently-reasoned blocking dependencies) — not a technical blocker, since none of the four capability-tickets (NIC-49/50/51/52) actually needs another's *output* to function: an open-position count for a company doesn't require that company's website summary to already exist.
- **Repo precedent directly supports building additive, independent modules without waiting for siblings to land first.** NIC-46 (CV attachment), NIC-47 (cover-letter attachment), NIC-48 (attachment filename builder), and NIC-56 (LinkedIn-saved-jobs importer) all shipped as standalone, reusable units; none blocked on a differently-numbered "foundation" ticket landing first, even where a later ticket (like NIC-53 here) was explicitly the one designed to assemble their outputs together.
- **The alternative (blocking) reading is inefficient with no compensating safety benefit.** NIC-49 (Todo) and NIC-51 (In Progress) do not share any file, function signature, or state that would make building NIC-51 first risky — the two capabilities are independent enough that whichever ships first can define the shared scaffold, and the other adds a sibling section. Blocking here would sit NIC-51 idle for no technical reason while its own two acceptance criteria (numeric count + source + date, for France and HQ) are fully buildable today using nothing NIC-49 would produce.
- **Concrete scaffold requirement (so the two tickets don't conflict later):** the new `SKILL.md` this ticket produces must be structured with clearly delimited, independently-headed sections (e.g., `## Company summary` placeholder note, `## Open positions (France / HQ country)` — this ticket's real content, `## Recent YouTube video`, `## Recent news` placeholders) so that NIC-49/50/52's Builders can each fill in their own section without needing to restructure the file NIC-51 leaves behind. This mirrors how `docs/ARCHITECTURE.md`'s per-job Notion template already reserves a labeled placeholder block per brief section (§3) — the same "reserve the slot, fill it incrementally" pattern, applied to the skill file itself.

**This is a Product Planner scope decision, made explicitly and with reasoning recorded here — not a silent default.** If Boss/Nicolas disagree (e.g., prefer NIC-49 to define the skill's overall shape first), that is a reasonable alternative and should be raised as feedback on this document before Builder starts; absent that feedback, Builder should proceed on Option (a).

## 5. Key scope questions (Boss's specific asks), answered explicitly

### 5.1 Data source(s) and ToS risk

**Decision: general web search (the `web_search`/`web_extract` tool class) against the company's own careers page and generic search-engine queries only. No LinkedIn browser automation, no credentialed/session-based access, no new paid Apify actor.**

This mirrors NIC-56's already-adjudicated LinkedIn constraint exactly, for the same reasons:
- AGENTS.md's forbidden-operations rule ("No contacting third parties... without explicit human approval") and PRD OQ-3 ("general web search/browsing... no new paid Apify actor") together rule out any dedicated LinkedIn scraping mechanism, any authenticated/cookie-based session against `linkedin.com`, and any new paid data-source integration.
- **LinkedIn Jobs search results are reachable via a plain, unauthenticated web search/fetch** (e.g., `web_search("site:linkedin.com/jobs <Company> France")` or fetching a LinkedIn Jobs search-results URL directly via `web_extract`) in the same way any other public search result is — this is categorically different from NIC-56's rejected mechanism, which required an **authenticated session acting as Nicolas** against a personal, logged-in page (`linkedin.com/jobs-tracker/?stage=saved`). A logged-out jobs-search-results page is public marketing content LinkedIn serves to any visitor (comparable to how Google/Bing index and cache these pages); no login wall or personal account state is involved. **However:** LinkedIn's public jobs-search pages sometimes rate-limit or partially block unauthenticated/automated-looking requests. This is a **reliability risk to plan a graceful-degradation path around (§5.3), not a ToS/approval risk** requiring a separate human sign-off, because no credential, cookie, or authenticated action is used.
- **Recommended source priority order** (Builder implements in this order, stopping at the first that yields a usable count):
  1. The company's own official careers page / job board (e.g., `careers.<company>.com`, Greenhouse/Lever/Workday-hosted boards linked from the company's site) — the most authoritative and most likely to have a live, filterable count. Reached via `web_search` to find the URL, then `web_extract`/browsing to read it.
  2. A generic web search for `"<company>" jobs France` / `"<company>" careers France` if no careers page is discoverable or the careers page has no country filter.
  3. A LinkedIn Jobs search (logged-out, public search-results page) as a fallback/cross-check only, via `web_search`/`web_extract` — never via `mcp__browser_*` tools with any stored session, never with credentials. If LinkedIn returns a "sign in to see all results" wall or blocks the request, treat that source as unavailable for this run and fall through to §5.3's degradation path rather than retrying with authentication.
- **Flag for Builder:** do not use `mcp__browser_navigate`/`mcp__computer_use` against `linkedin.com` in a way that persists cookies, logs in, or otherwise establishes a session — general search-engine-style fetch/read only, exactly as NIC-56 drew the line.

### 5.2 How "France" vs. "HQ country" is derived

**Decision: the skill independently researches the company's HQ location as part of this ticket's own work — it is not assumed to be present as job/Notion-card metadata.**

Reasoning: the existing Notion Kanban schema (per `docs/ARCHITECTURE.md`, NIC-42) has exactly four non-title properties — `Status`, `Company`, `Role`, `Priority` — none of which encode a headquarters country. The job posting itself (source of "Company"/"Role") also does not reliably state HQ location (a France-based job listing at a US company doesn't imply the poster stated "HQ: USA"). Therefore:
1. **France is always evaluated** — this is fixed, not derived (the ticket/PRD frame "positions in France" as the baseline count Nicolas always wants, since he is job-hunting in France).
2. **HQ country is determined via the same web search/browsing mechanism as §5.1**, typically surfaced incidentally while reading the company's official website ("About"/"Contact"/footer address) or careers page (which commonly states "Headquartered in <city, country>") — i.e., this does not require a second, separate research pass; it is read opportunistically from the same page(s) already being fetched for the count itself, or from one additional lightweight search if not found there (e.g., `"<company>" headquarters`).
3. **If HQ country cannot be confidently determined:** state that explicitly ("HQ country could not be determined from available sources") rather than guessing from indirect signals (e.g., stock exchange listing, domain TLD, or founder nationality) — consistent with the "never fabricate" rule. In that case, only the France count is reported.
4. **If HQ country determination resolves to France:** per FR-A5's own acceptance criterion, state that explicitly ("Headquartered in France — see France count above") instead of computing/duplicating a second identical count.

### 5.3 Graceful degradation when a precise count is not available

**Decision: three explicit, distinct output states per country, never silently collapsed into each other:**

| State | When it applies | Required output |
|---|---|---|
| **Exact count** | Source shows a clean, filterable number (e.g., careers page "23 open positions in France" or a LinkedIn/job-board search results count) | The number, verbatim, + source name/URL + retrieval date. |
| **Approximate / range** | Source only shows "X+ openings," a range, or a count that includes non-France/non-HQ-country postings mixed in with no clean filter (e.g., "50+ jobs worldwide" with no per-country breakdown available) | State the approximate/range value **exactly as shown**, explicitly labeled as approximate (e.g., "50+ (worldwide total; no France-specific breakdown found)") + source + retrieval date. Never silently convert an approximate figure into a bare number, and never estimate/interpolate a country-specific figure from a worldwide total. |
| **Could not determine** | No source yields any usable count (careers page has no job listings/count for the country, LinkedIn search is blocked/inaccessible, and no other web result surfaces one) | Explicit "could not determine open-position count for <country>" statement, naming which source(s) were checked and what happened (e.g., "careers page shows no country filter; LinkedIn search returned no accessible results"). **Never** report a 0, a blank, or an invented placeholder number in this case — 0 is a valid *found* answer (a real "no open roles currently" state) and must never be used to mean "we didn't find data." |

This three-state model directly operationalizes the PRD's "never fabricate" hard rule for this specific data type (counts, which are especially tempting to round or estimate) and gives Builder an unambiguous decision tree instead of an open-ended "handle gracefully" instruction.

### 5.4 Output contract (source + retrieval date, concrete structure)

**Decision: a small structured Python dict/JSON object per country, plus a rendered plain-text block for the skill's own conversational output — both produced by the same function, so NIC-53's future Notion-attach step consumes the structured form directly rather than re-parsing prose.**

Recommended shape (Builder may adjust field names to match whatever convention NIC-49 establishes for the rest of the brief, but the shape/semantics below must be preserved):

```json
{
  "france": {
    "status": "exact",               // "exact" | "approximate" | "not_found"
    "count": 23,                     // int if status=="exact"; string as-shown if "approximate" (e.g. "50+"); null if "not_found"
    "source_name": "Acme Corp careers page",
    "source_url": "https://acme.example/careers?country=fr",
    "retrieved_date": "2026-09-12",
    "note": null                      // free-text caveat, required when status != "exact" (e.g. why approximate/not found)
  },
  "hq_country": {
    "country": "Germany",             // null if undetermined
    "same_as_france": false,          // true short-circuits the block below per FR-A5
    "status": "exact",
    "count": 8,
    "source_name": "Acme Corp careers page",
    "source_url": "https://acme.example/careers?country=de",
    "retrieved_date": "2026-09-12",
    "note": null
  }
}
```

- When `hq_country.same_as_france` is `true`, `country`/`count`/`source_*`/`note` fields are omitted or null — the skill's rendered text output states "Headquartered in France — see France count above" per FR-A5, and the structured object signals this via the boolean rather than duplicating the France block.
- `retrieved_date` is always the date the count was actually fetched (this run), never a cached/older date — consistent with FR-A4's "since counts change" rationale.
- The plain-text rendering for chat/Notion prose should read naturally, e.g.: *"Open positions in France: 23 (source: Acme Corp careers page, acme.example/careers?country=fr, retrieved 2026-09-12). Open positions in Germany (HQ): 8 (same source, same date)."* — Builder has latitude on exact phrasing; the structured dict above is the binding contract for NIC-53's future programmatic consumption, not the prose wording.
- This is a **recommendation, not a rigid API Builder must match byte-for-byte** — the binding requirement is that *some* structured, machine-readable form exists per country with these five semantic fields (status, count-or-null, source, URL, retrieval date), so NIC-53 doesn't have to regex-parse conversational text later.

### 5.5 Implementation form confirmation

**Confirmed: Python module(s) and/or skill Markdown text only, following this repo's existing pattern.** Concretely:
- A new `SKILL.md` at `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` (v1 repo, same location pattern as `kanban-status`), containing the skill's frontmatter, trigger description, and this ticket's procedure (source priority order, France/HQ derivation, degradation rules, output contract) as documented Markdown instructions for the agent to follow — consistent with how `kanban-status`, `cv-match`, `write-outreach`, etc. are implemented (a described procedure the agent executes using existing tool calls, not a standalone running service).
- Optionally, a small dependency-light Python helper module (e.g., a `scripts/`-style helper mirroring the v1 repo's existing pattern) **only if** Builder finds a genuine need for deterministic parsing/formatting logic beyond what a described procedure can reliably specify (e.g., formatting the structured dict in §5.4) — using only `urllib`/stdlib or already-available `web_search`/`web_extract`/`browser_*` tool calls, no new pip dependency, no new virtualenv.
- **No new backend, database, or web app of any kind** — this repeats AGENTS.md's explicit prohibition and this repo's already-rejected Atoms-Cloud-based architecture (see the canceled NIC-5/NIC-6-class tickets). The architecture remains Notion-as-system-of-record + Claude Code skills + (later, Phase 5) n8n polling — nothing here changes that.

## 6. Scope

### 6.1 In scope
1. Create `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` (new directory, v1 repo) with:
   - Frontmatter + trigger description for the overall `company-research` skill (per PRD Section 6.1/OQ-7's framing — even though only this ticket's capability is implemented today, the frontmatter should describe the skill's eventual full scope so future tickets extend rather than rewrite it).
   - A clearly delimited section for open-position counts (France + HQ country) implementing §5.1–§5.4 above in full.
   - Clearly labeled placeholder sections/headings for the sibling capabilities (company summary, YouTube video, recent news) reserved for NIC-49/50/52, per §4's scaffold requirement — empty/stub content only, no invented capability.
2. The source-priority procedure (§5.1), France/HQ derivation logic (§5.2), three-state degradation model (§5.3), and the structured output contract (§5.4), all documented precisely enough for independent verification.
3. At least one real, end-to-end test run against a real company (Builder's choice of a plausible target, e.g. a company already referenced elsewhere in this repo's test data or a real company Nicolas might realistically research) demonstrating: an exact-count case, and ideally one degraded case (approximate or not-found) — using real web search/fetch calls, not fabricated/hand-written "example" output presented as if it were a real result.
4. `docs/ARCHITECTURE.md` and `docs/PLAN.md` entries documenting the design decision, the scaffold structure, and verification evidence, per established repo pattern (NIC-42/43/44/46/47/48/56/62 precedent).

### 6.2 Out of scope (explicitly)
- Company/website summary content (NIC-49), YouTube video lookup (NIC-50), recent news (NIC-52) — this ticket only reserves labeled placeholder sections for them; it must not attempt to implement or stub *fake* content for those capabilities.
- Attaching the brief to the Notion job page, or wiring `company-research` as the `company-intel` source for `write-outreach`/`run-my-week` — both are NIC-53's explicit scope, which depends on all four sibling tickets (§3, §4).
- Any LinkedIn browser automation, credentialed/session-based access, or scraping of authenticated LinkedIn pages — hard out of scope per §5.1, same class of restriction as NIC-56.
- Any new paid Apify actor or other paid third-party data source — ruled out by PRD OQ-3.
- Any new backend, database, or web application — ruled out by AGENTS.md and this repo's already-rejected prior architecture (§5.5).
- Estimating or interpolating a country-specific count from a worldwide/mixed total — explicitly forbidden by §5.3's degradation model (must be labeled "approximate"/"not found," never computed/guessed).
- Editing `run-my-week`, `write-outreach`, `cv-match`, `interview-prep`, or `kanban-status` — this ticket only adds a new, standalone skill directory; it does not touch any existing skill file.
- Any Notion API calls, Notion schema changes, or Notion card creation/mutation — this ticket produces a skill procedure only; NIC-53 handles Notion attachment.

## 7. Acceptance criteria (numbered, testable — extends the ticket's own two ACs)

| # | Criterion | Traces to | Testable check |
|---|---|---|---|
| AC1 | Given a real company name, the skill produces a France open-position count that is either an exact number, an explicitly-labeled approximate/range value, or an explicit "could not determine" statement — never a fabricated or silently-estimated number. | FR-A4, §5.3 | Run against ≥1 real company; inspect output against the three-state table in §5.3; confirm no bare number appears without a `status` label backing it. |
| AC2 | Every France count (in any of the three states) is accompanied by a named source and a retrieval date matching the day the check was actually run. | FR-A4 | Inspect output; `source_name`/`source_url`/`retrieved_date` present and non-fabricated (retrieval date must match session date, not an invented or cached-looking date). |
| AC3 | The HQ country is independently determined via web research (not assumed from job/Notion metadata), and if it cannot be confidently determined, that is stated explicitly rather than guessed. | §5.2 | Code/procedure review confirms no reliance on a Notion property or job-posting field for HQ country; test run includes at least one case where HQ determination is attempted from company-website/careers-page content. |
| AC4 | If HQ country equals France, the skill states this explicitly instead of duplicating the France count under a second heading. | FR-A5 | Test with a real France-HQ'd company; confirm output text says something equivalent to "Headquartered in France — see above," not a second identical count block. |
| AC5 | If HQ country differs from France, the HQ count follows the same three-state model and sourcing standard as AC1/AC2. | FR-A5 | Test with a real non-France-HQ'd company; confirm the HQ block has the same status/source/date structure as the France block. |
| AC6 | The skill's output includes a structured, machine-parseable representation of both counts (not prose-only), following the §5.4 contract's semantics (status/count/source/URL/date per country, `same_as_france` flag). | §5.4 (NIC-53 forward-compatibility) | Inspect Builder's actual output artifact/return value; confirm the five semantic fields exist per country block, even if exact key names differ from §5.4's example. |
| AC7 | No call to `linkedin.com` in this skill's implementation uses stored session state, cookies, or credentials; any LinkedIn access is a plain, unauthenticated search/fetch used only as a fallback source. | §5.1, AGENTS.md forbidden-operations | Code/procedure review confirms zero credential/session-handling code for LinkedIn; if LinkedIn is used in the test run, confirm it was a logged-out `web_search`/`web_extract` call, not `browser_*` with persisted auth. |
| AC8 | No new paid Apify actor, no new backend/database/web app, and no pip dependency beyond stdlib/already-available tool calls are introduced. | PRD OQ-3, AGENTS.md, §5.5 | `git diff`/file listing review confirms only `SKILL.md` (+ optional stdlib-only helper script) added; no `requirements.txt`/new service/new dependency manifest changes. |
| AC9 | The new `SKILL.md` reserves clearly labeled, empty placeholder sections for company summary, YouTube video, and recent news (NIC-49/50/52), without inventing content for them. | §4, §6.1 | Read the shipped `SKILL.md`; confirm headings exist for the three sibling capabilities and contain only a "pending — see NIC-49/50/52" style placeholder, no fabricated example content presented as real. |
| AC10 | At least one test run used a real company via real web search/fetch calls — not a hand-written "simulated" example presented as if it were live output. | Ticket's implicit evidence bar (FACTORY_PROTOCOL.md: no unverified claims) | Builder's evidence explicitly names the real company/source URLs used and states plainly this was a real, live run. |

## 8. Effort estimate

**S — approximately 2–3 hours.** Reasoning: this is a net-new, standalone skill file (first `company-research` work in the repo), but the actual logic is narrow — one capability (counts, two countries) with a straightforward three-state degradation model and no Notion API calls at all (unlike NIC-42/43/46/47/48/56, all of which touched live Notion state and needed test-card create/verify/archive cycles). Breakdown: skill scaffold + frontmatter + placeholder sections (~20–30 min), source-priority search/fetch procedure + France/HQ derivation logic (~45–60 min, the main new-logic component), degradation-state handling + output-contract formatting (~30 min), one real end-to-end test run against a real company with evidence capture (~30–40 min), documentation (`ARCHITECTURE.md`/`PLAN.md` entries, ~15–20 min). Comparable in size to NIC-44 (design-only skill, no Notion writes) rather than the larger Notion-attachment tickets.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| LinkedIn's public jobs-search pages may rate-limit, CAPTCHA, or partially block unauthenticated automated-looking requests, making LinkedIn an unreliable fallback source in practice. | Medium | Treat LinkedIn strictly as fallback/cross-check (§5.1), never a required source; a blocked/inaccessible LinkedIn attempt routes straight to the "could not determine" state (§5.3) rather than retrying with any form of authentication. |
| Career-page job counts are frequently aggregated across offices/countries with no clean per-country filter, especially for smaller companies. | Medium–High (this is the most likely real-world failure mode) | §5.3's "approximate/range" state exists specifically for this; Builder must resist the temptation to compute a per-country estimate from a worldwide total — that is explicitly forbidden. |
| HQ country can be genuinely ambiguous for some companies (multiple large offices, holding-company structures, recently relocated HQ). | Medium | §5.2's "could not confidently determine" fallback covers this; Builder should not pick a "most likely" HQ from conflicting signals — state the ambiguity instead. |
| This ticket's "reserve placeholder sections for siblings" scaffold (§4/§6.1/AC9) could still end up needing rework once NIC-49 actually ships, if NIC-49's Builder makes structural choices (e.g., frontmatter fields, file organization) this ticket didn't anticipate. | Low–Medium | Accepted risk of the Option (a) decision in §4 — the alternative (blocking) has a worse expected cost (idle ticket, no technical benefit) per §4's reasoning. Recommend Builder keep the scaffold minimal/conventional (plain Markdown headings, no elaborate structure) specifically to minimize rework surface if NIC-49 reshapes the file later. |
| Retrieval-date discipline (AC2) depends on the skill actually being re-run close to when its output is used — a brief generated once and reused weeks later would have a stale, misleading date. | Low (inherent to the feature, not this ticket's design) | Out of this ticket's control (a caching/freshness policy for the overall brief is more naturally NIC-53's or a future ticket's concern); flagged here for awareness, not blocking. |

## 10. Open questions

- **OQ-1 (not blocking):** Should the `company-research` skill's frontmatter/trigger description be authored now (this ticket, describing the *eventual* full 4-part brief) or left minimal and expanded incrementally by each sibling ticket? Recommendation: author it now, describing the full eventual scope (per PRD Section 6.1), since a stub trigger description costs nothing extra and gives Nicolas a coherent invocation phrase from the first ticket onward rather than four incrementally-rewritten versions.
- **OQ-2 (not blocking, flag to Boss/Nicolas per this repo's precedent for new v1-repo files):** Confirm the `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` location is acceptable, consistent with how NIC-44's OQ-1 flagged the same class of question for `kanban-status`. Recommendation stands (§5.5) but is surfaced explicitly, not silently assumed.
- **OQ-3 (not blocking):** Exact field-naming for the §5.4 structured output contract is left to Builder's discretion (the semantics, not the literal key names, are binding) — recommend Builder align naming with whatever convention NIC-49 establishes for the rest of the brief, if NIC-49 lands first; otherwise Builder's naming becomes the convention NIC-49/50/52 should follow.
- **No blockers to starting Builder work.** The one substantive judgment call in this document — proceeding without waiting for NIC-49 (§4) — is made explicitly with reasoning recorded, not left as a silent assumption; Boss/Nicolas can override it before Builder starts if they disagree.

## 11. Go/no-go recommendation

**GO — Option (a) scaffold-now approach (§4), scoped exactly as §6.1/§6.2 describe.** This ticket is buildable today with zero technical dependency on NIC-49/50/52 actually shipping first (their described "dependency" in the ticket text is best read as descriptive/sequencing convenience, not a technical blocker — confirmed via NIC-53's own description, which is the ticket that genuinely needs the full set). No AGENTS.md forbidden-operation is implicated: no deployment, no destructive operation, no secret exposure, and no unauthorized third-party contact (LinkedIn access, if used at all, is limited to logged-out, unauthenticated, generic search/fetch — never a credentialed session, per §5.1's explicit distinction from NIC-56's rejected mechanism). Builder should proceed directly to implementation.

---

## HANDOFF TO BUILDER

**Objective:** Create the `company-research` skill scaffold in the v1 repo (`/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md`) implementing the open-positions-count capability (France + HQ country) per FR-A4/FR-A5, with placeholder sections reserved for the three sibling capabilities (company summary, YouTube video, recent news) so NIC-49/50/52 can extend the same file later without conflict.

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2` (this scope doc, `docs/ARCHITECTURE.md`, `docs/PLAN.md` — documentation updates only).
- Repo: `/home/nicow/cv-job-match` (v1) — where the new skill file itself is created: `.claude/skills/company-research/SKILL.md` (new directory).
- `/home/nicow/cv-job-match/.claude/skills/kanban-status/SKILL.md` — structural precedent for a small, standalone, additive skill file (frontmatter format, "Empirical test evidence" section pattern for documenting real test runs).
- `/home/nicow/cv-job-match/.claude/skills/run-my-week/SKILL.md` and `write-outreach/SKILL.md` — for the existing `company-intel` references this skill will eventually replace (NIC-53's job, not this ticket's, but useful context for the frontmatter's eventual-scope description, OQ-1).
- This document (`docs/handoffs/NIC-51-product-planner-scope-validation.md`) for full rationale, the dependency-sequencing decision (§4), the data-source/ToS decision (§5.1), France/HQ derivation (§5.2), degradation model (§5.3), and the output contract (§5.4).

**Constraints:**
- **Hard stop: no LinkedIn browser automation, no credentialed/session-based access, no stored cookies** — any LinkedIn use must be a plain, logged-out `web_search`/`web_extract`-style fetch, used only as a fallback/cross-check source (§5.1). Verify via AC7.
- **No new paid Apify actor, no new backend/database/web app, no new pip dependency** beyond stdlib or already-available tool calls (§5.5). Verify via AC8.
- **Never estimate or interpolate a country-specific count from a worldwide/mixed total** — use the explicit three-state model (exact / approximate-labeled / could-not-determine) in §5.3. A found "0 open roles" is a valid exact answer and must never be conflated with "could not determine."
- **Do not implement or stub fake content for NIC-49/50/52's capabilities** — placeholder headings only, clearly marked pending (AC9).
- Do not touch `run-my-week`, `write-outreach`, `cv-match`, `interview-prep`, or `kanban-status` — this ticket only adds a new, standalone file.
- No Notion API calls, no Notion schema/card changes — out of scope (NIC-53's job).
- No deployment, no destructive/irreversible operation, no secret exposure, no unauthorized third-party contact.
- Do not fabricate test evidence — any example company/count used as evidence must be from a real, live web search/fetch run, explicitly named as such (AC10).

**Acceptance criteria:** AC1–AC10 in §7 above.

**Files likely to touch:**
- New: `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` (v1 repo).
- Optional new: a small stdlib-only helper script if Builder finds deterministic parsing/formatting logic genuinely needed beyond what a described procedure can specify (§5.5) — document if added, and where.
- `docs/ARCHITECTURE.md` (this repo) — new "NIC-51" section (design decision, source-priority procedure, output contract, real test-run evidence).
- `docs/PLAN.md` (this repo) — new NIC-51 entry, following existing Phase 3 formatting; note that the scaffold is ready for NIC-49/50/52 to extend.

**Recommended next action:** Builder creates the skill scaffold with the open-positions-count logic fully implemented per §5.1–§5.4, runs at least one real end-to-end test against a real company (ideally including one degraded-state case), documents evidence (real source URLs, real retrieval dates, real output), updates `ARCHITECTURE.md`/`PLAN.md`, and hands off to QA Reviewer with the AC1–AC10 table above as the verification checklist. QA should independently re-derive at least one test run itself (e.g., re-checking a stated source URL actually shows the claimed count) rather than accepting Builder's self-report alone, per FACTORY_PROTOCOL.md's independence rule.
