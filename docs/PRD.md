# PRD — cv-job-match v2: Notion-Centric Job Search Copilot

**Author:** PRDCraft (for Nicolas Wajs)
**Date:** 2026-09-10
**Source repo reviewed:** [github.com/NicolasWs/cv-job-match](https://github.com/NicolasWs/cv-job-match) (public, read via web browse — README.md, CLAUDE.md, docs/USER-GUIDE.md, config/search-profile.yaml, tracker/job-tracker-model.md, and all five `.claude/skills/*/SKILL.md` files, as of commit `34b62b8`, Sep 7 2026)
**Status:** Draft for review — updated after scoping Q&A round with Nicolas (all decisions below marked **[RESOLVED]**)

**Resolved scoping decisions (this session):**
1. Rebuild keeps automated n8n weekly scrape + `find-opportunities` scanning; rebuild targets "job selected" onward.
2. Files (tailored CV, cover letter) attach natively to Notion pages, not Google Drive.
3. Kanban statuses = the six specified **plus** `offer` / `rejected` / `withdrawn` as terminal states.
4. "Questions to ask the interviewer" stays a subsection of the existing interview cheat sheet (no separate deliverable), now tailored using the company research brief.
5. Company research becomes **one new skill** (working name `company-research`) that both produces the full brief (website/video/headcount/news) **and** fills the previously-undocumented `company-intel` gap referenced by `write-outreach`/`run-my-week`.
6. The existing autonomous "CV Coach" cron pipeline (9.3/10-gated) is **deprecated**; its logic folds into the new unified flow so every job — not just ultra-high scorers — gets research + cheat sheet.
7. Company research retrieval uses **general web search/browsing** (no new paid Apify actors for now).
8. **No backfill** — v2 starts fresh from newly selected jobs; the old Google Sheet stays as historical record only.
9. Notion keeps the **final version only** of tailored CV / cover letter (not every refinement-loop iteration).
10. **New requirement surfaced in Q&A:** moving a Kanban card should trigger agent work automatically (e.g., dragging a card to a new status kicks off the next skill), not just record status passively. Mechanism: **extend the existing n8n instance with a Notion-polling workflow** that detects status changes and triggers the appropriate skill/pipeline step — reusing the same automation platform already used for the weekly scrape, rather than standing up a new webhook service.
11. New Kanban database lives under the existing Notion "Job Search" parent page (`coach.notion_parent_page_id`).

---

## 1. Executive Summary

`cv-job-match` is Nicolas's personal, Claude-skill-based job search pipeline for Product Manager (AI/Data, Paris) roles. It already automates weekly job scraping (n8n + Apify), scoring against a CV, tailored CV generation, outreach drafting, and interview prep — coordinated through five Claude Code skills (`find-opportunities`, `cv-match`, `write-outreach`, `interview-prep`, `run-my-week`) and tracked in a Google Sheet.

This PRD scopes a **v2 rebuild** that:
1. Keeps the existing automated discovery layer (n8n weekly scrape + `find-opportunities` multi-board scan and scoring) as the top of funnel — **confirmed by user**.
2. Adds a new **Company Research** capability per job (one new `company-research` skill): company website summary, a recent YouTube video, open-position counts in France and in the company's headquarters country, and significant recent news tied to the job opportunity — this does not exist in the current repo today, and also fills the previously-undocumented `company-intel` gap referenced by `write-outreach`/`run-my-week`.
3. Rebuilds the per-job workflow from "job selected" onward around **Notion** as the system of record: a Kanban board with a fixed status set (including terminal states), one Notion page per job holding the tailored CV and cover letter as **native Notion attachments** (final version only, replacing the current Google Drive folder-per-job model), and an interview cheat sheet page — extending to *every* application, replacing the current "CV Coach" autonomous pipeline, which is deprecated in favor of this unified flow.
4. Retains interview-question generation (Q&A + STAR + cheat sheet, including "questions to ask the interviewer" as a cheat-sheet subsection) and cover-letter adaptation, both of which already exist as skills and are being re-platformed onto Notion rather than reinvented from scratch.
5. Replaces the Google Sheets tracker (`tracker/job-tracker-model.md`) with a Notion database whose status values match Nicolas's stated process plus terminal states: `selected → cv scored → cover letter done → applied → first interview → second interview → offer / rejected / withdrawn`.
6. **New:** moving a card between statuses on the Notion Kanban should be able to trigger the corresponding agent work automatically, via an n8n workflow that polls the Notion database for status changes and invokes the right skill — extending the existing n8n automation platform rather than introducing new infrastructure.

## 2. Problem & Evidence

### 2.1 Problem statement
Nicolas runs a solo, high-volume job search (PM, AI/Data, Paris and adjacent markets) and has already built substantial automation, but two gaps remain, per his direct request:
- He has no systematic way to research a target company beyond what's in a job description before applying or interviewing (website positioning, hiring signal via video/news, real headcount/opening scale in France vs HQ country).
- His tracking and file organization live across a Google Sheet, local folders, and Google Drive, rather than one place (Notion) he wants to standardize on, with a Kanban view matching how he actually thinks about pipeline stages.

### 2.2 Evidence from the existing repo (sourced, not assumed)
| Evidence | Source |
|---|---|
| Weekly n8n scrape (Apify → filter → dedupe → Drive JSON) is live and documented as the only non-conversational step. | README.md :cite[c33] |
| `find-opportunities` skill scans 4 boards, scores 0–10, produces a "Company Radar" — but the radar only records `Angle` (which CV proof point to lead with) and `CV variant`, no external company research (site/video/news/headcount). | `.claude/skills/find-opportunities/SKILL.md` |
| `cv-match` skill already does CV parsing, fit scoring (Strong/Good/Partial), and a tailored-CV refinement loop with a blind critic subagent. | `.claude/skills/cv-match/SKILL.md` |
| `write-outreach` skill already drafts cover letter (~250–300 words), recruiter email, and LinkedIn message, with its own refinement loop. | `.claude/skills/write-outreach/SKILL.md` |
| `interview-prep` skill already produces a Q&A set, STAR stories, and a one-page cheat sheet — but only "offer[s] to export the support sheet to a Google Doc," no Notion integration in this skill itself. | `.claude/skills/interview-prep/SKILL.md` |
| Current tracker is a Google Sheet with statuses `To apply → Applied → Screening → Interview 1 → Interview 2 → Final → Offer → Rejected → Withdrawn` — different status set and different tool than what Nicolas now wants. | `tracker/job-tracker-model.md` |
| A separate, already-built "CV Coach" autonomous pair (`scan-jobs` + `prep-application`, run via a Hermes cron job outside this repo) **already publishes a Notion interview cheat-sheet page** per job, but only auto-triggers for postings scoring **≥9.3/10** Fit Score — the vast majority of applications never get this Notion artifact today. | README.md "CV Coach" section, `config/search-profile.yaml` (`coach.notion_parent_page_id`, `coach.auto_prep_min_score: 9.3`) |
| Generated packages currently land in local `applications/{date}_{Company}_{Role}/package.md` and mirror to a Google Drive subfolder — no Notion file storage today. | CLAUDE.md, README.md |
| Hard rule already enforced across all skills: never fabricate experience/metrics; never auto-apply or auto-message; always draft for human send. | CLAUDE.md "Hard rules" |

### 2.3 Evidence explicitly not available
- No access to Nicolas's actual Notion workspace, its existing pages/databases, or API credentials — cannot confirm what (if anything) already exists there beyond the one cheat-sheet parent page ID in the config.
- No access to real usage data (how many jobs actually run through the pipeline weekly, drop-off rates, time spent per stage) — this PRD cannot quantify current effort/time savings; treat any such number in this document as an estimate to validate, not a measured fact.
- No visibility into which "significant news" sources or YouTube retrieval mechanism Nicolas already has access to (e.g., an Apify actor, a search API) — the research capability's technical approach is a set of options, not a confirmed architecture.

## 3. Target User & Use Cases

**Target user:** Nicolas Wajs, sole user, Product Manager (AI/Data) actively job-searching, technically capable of running Claude Code / Cowork sessions and editing YAML/Markdown config.

**Primary use cases (this PRD's scope):**
1. Given a job Nicolas is about to apply to (whether sourced automatically or pasted manually), produce a structured company research brief before deciding to invest further.
2. Given the job + CV, generate interview questions to prepare (both questions Nicolas should expect and questions he should ask the interviewer).
3. Given the job description, produce a tailored cover letter.
4. Track every job that reaches "selected" status through to interview outcomes on a Notion Kanban board with organized per-job files.
5. Have a single Notion cheat sheet per job to review right before an interview.

## 4. Goals

- G1: Every job Nicolas decides to pursue gets a company research brief (website, video, headcount/openings by country, relevant news) without manual searching.
- G2: Interview question prep (candidate-side Q&A and interviewer-directed questions) is generated consistently for every job that reaches an interview stage.
- G3: Cover letters are tailored per job description, reusing the existing quality bar (grounded in CV facts, no fabrication).
- G4: Pipeline state for every pursued job lives in one Notion Kanban board with the status set Nicolas specified, replacing the Google Sheet as the tracker of record.
- G5: Each job's working files (tailored CV, cover letter) and interview cheat sheet are attached natively to that job's Notion page — one place to open before interviewing or applying.

## 5. Non-Goals

- Not rebuilding or replacing the automated weekly scraping layer (n8n/Apify/`find-opportunities`) — it is retained as-is per the confirmed scoping decision, and is out of scope for changes in this PRD beyond whatever handoff is needed into the new Notion flow.
- Not adding auto-apply or auto-messaging of any kind — the existing hard rule (drafts only, human sends) carries over unchanged.
- Not building a multi-user or shared product — this remains a personal tool for Nicolas.
- Not migrating historical data from the existing Google Sheet tracker or Drive folders into Notion (see Open Question OQ-4 on whether a one-time backfill is wanted).
- Not specifying a replacement for the existing CV-scoring or CV-tailoring logic in `cv-match` — that skill's approach (Match Score, refinement loop) is assumed retained; this PRD only changes where its *output* is filed (Notion instead of local/Drive).

## 6. Scope

### 6.1 In scope
- **New: `company-research` skill** — one brief per job covering: company website summary, most recent relevant YouTube video (if findable), count of open positions in France, count of open positions in the company's headquarters country (if different from France), and significant recent news connected to the job/hiring context (e.g., funding round, expansion, leadership change, product launch). Built via general web search/browsing (no new paid Apify actor for v1). This skill also becomes the `company-intel` source consumed by `write-outreach` and `run-my-week`, closing the gap left by the currently-undocumented/missing `company-intel` reference.
- **Interview questions for the interviewer** — stays within the existing `interview-prep` skill's one-page cheat sheet as its "Questions to ask them" subsection; the only change is that these questions must now be tailored using the new company research brief, not left generic.
- **Rebuilt: Notion Kanban tracker** — new Notion database under the existing "Job Search" parent page, one card per job, status property: `selected, cv scored, cover letter done, applied, first interview, second interview, offer, rejected, withdrawn` — replacing `tracker/job-tracker-model.md` (Google Sheet), which is retained read-only for historical reference (no backfill into Notion).
- **Rebuilt: Per-job file organization** — one Notion page per job (linked from its Kanban card) with the tailored CV and cover letter attached as native files, final version only (refinement-loop intermediate drafts are not retained in Notion).
- **Rebuilt/extended: Notion interview cheat sheet** — generated for every job that reaches an interview stage, replacing the current CV Coach's 9.3/10-gated auto-trigger; every job gets this, not only ultra-high scorers.
- **New: n8n Notion-status-change automation** — an n8n workflow polls the Notion Kanban database on a schedule, detects status transitions, and triggers the appropriate skill/pipeline step (e.g., moving a card to `cv scored` kicks off `cv-match`, moving to `cover letter done` kicks off `write-outreach`) — see FR-G.
- **Deprecated as part of this rebuild:** the existing autonomous "CV Coach" Hermes cron pair (`scan-jobs` + `prep-application`) and its 9.3/10 auto-trigger threshold — folded into the unified Notion-driven flow above.
- **Carried over unchanged (confirmed in scope to keep, not to modify):** weekly n8n scrape, `find-opportunities` scanning/scoring, `cv-match` scoring and tailoring logic, `write-outreach` cover letter drafting logic, `interview-prep` Q&A/STAR logic, the "never fabricate / never auto-send" hard rules.

### 6.1.a LinkedIn Saved Jobs input path (addendum, NIC-56)

**Addendum, added post-ship (2026-09-11):** in addition to the automated n8n/`find-opportunities` discovery layer (Section 6.1 above), Nicolas can also seed `selected`-status Notion cards from his LinkedIn Saved Jobs list via a manual/semi-automated path: he copies his saved-jobs list from his own already-logged-in browser, reformats it into a small pipe-delimited text file, and runs `scripts/notion_import_saved_jobs.py` against it. The script itself never accesses `linkedin.com` in any form (no browser automation, no session cookies, no scraping) — it only parses the manually-provided text and calls the Notion API, reusing NIC-43's `build_job_page_children()` card-creation shape and NIC-56's own deduplication logic. This is a second, independent input path alongside the n8n discovery layer, not a replacement for it; see `docs/ARCHITECTURE.md`'s "NIC-56" section for full design detail.

### 6.2 Out of scope
- Any change to how jobs are discovered or scored before "selected" status.
- Any UI beyond Notion itself (no new web app, no changes to the existing `app/server.py` local Flask app implied by this PRD unless a future phase decides otherwise).
- Multi-CV-format support beyond what already exists (EN/FR/auto).

## 7. Functional Requirements

Requirements are grouped by capability. Each has an ID for traceability into user stories (Section 13).

### FR-A — Company Research
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-A1 | Given a company name (and ideally a job URL), the system produces a company research brief. | Brief is generated on request for any job in `selected` status or later; failure to find a data point is stated explicitly, never fabricated. |
| FR-A2 | Brief includes a short company/website summary. | Summary reflects the company's own site content (product, market, positioning) in 3–5 sentences, with the source URL cited. |
| FR-A3 | Brief includes a link to the most recent relevant YouTube video about the company, if one exists. | If found: title, publish date, URL. If none found within a reasonable recency window (recommendation: 12 months — needs validation, OQ-3), state "no recent video found" rather than substituting an old or irrelevant one. |
| FR-A4 | Brief includes the count of open positions at the company in France. | Numeric count + source (e.g., company careers page, LinkedIn jobs search) + retrieval date, since counts change. |
| FR-A5 | Brief includes the count of open positions in the company's headquarters country, when different from France. | Same sourcing standard as FR-A4; if HQ is France, state that explicitly instead of duplicating the count. |
| FR-A6 | Brief includes significant recent news connected to the job opportunity (funding, expansion, leadership change, restructuring, product launch, etc.). | 1–3 news items max, each with a one-line "why this matters for this application" note, dated, sourced. |
| FR-A7 | The brief is attached to the job's Notion page. | Brief appears as a Notion block/section on the job's page, not only in chat output. |

### FR-B — Interview Question Preparation
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-B1 | System generates candidate-facing interview Q&A for a given job (reusing existing `interview-prep` scope: strengths/weaknesses, "tell me about yourself," "why this company," behavioral questions). | Matches current skill's documented output structure; every metric traces to the CV, no invented figures. |
| FR-B2 | System generates questions Nicolas should ask the interviewer, tailored to the company research brief (FR-A) and the role, as a subsection of the existing one-page cheat sheet. **[RESOLVED — stays within cheat sheet, not a separate deliverable]** | 4–5 questions in the cheat sheet's existing "Questions to ask them" section, each tied to a specific fact from the company research brief or JD, not generic filler. |
| FR-B3 | Output is written to the job's Notion cheat sheet, not only chat. | Cheat sheet page contains both Q&A and interviewer questions as separate, scannable sections. |

### FR-C — Cover Letter Adaptation
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-C1 | System drafts a cover letter tailored to the specific job description, reusing the existing `write-outreach` logic and quality bar. | Matches current skill's ~250–300 word target, native language match to the posting, no fabricated claims. |
| FR-C2 | Cover letter is refined (existing refinement-loop behavior retained where the Agent/subagent tool is available). | Loop behavior unchanged from current `write-outreach` skill; degrades gracefully to single-pass review outside Claude Code/Cowork, as today. |
| FR-C3 | Final cover letter is stored as a native file attachment on the job's Notion page. | File is attached to the Notion page (not just linked to Drive), per the confirmed decision. |

### FR-D — Notion Kanban Tracker
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-D1 | A Notion database exists with one entry (card) per job being pursued. | Database is queryable/filterable by status, company, role, priority. |
| FR-D2 | Status property uses exactly the values Nicolas specified, plus terminal states. **[RESOLVED]** | Statuses: `selected`, `cv scored`, `cover letter done`, `applied`, `first interview`, `second interview`, `offer`, `rejected`, `withdrawn`. |
| FR-D3 | Each card links to a full Notion page for that job containing: job details, company research brief, tailored CV file, cover letter file, and cheat sheet. | Opening a card's page surfaces everything needed for that job in one place, no cross-tool hopping required. |
| FR-D4 | Status transitions can be triggered conversationally (e.g., "mark Mistral as applied") consistent with how the rest of the pipeline is operated today. | A natural-language status update request results in the correct Notion property change, matching the interaction style of existing skills (e.g., "add Amundi to my target companies" pattern in README). |
| FR-D5 | The Notion tracker becomes the single source of truth for pipeline status, replacing the Google Sheet tracker. **[RESOLVED]** | `tracker/job-tracker-model.md` (Google Sheet) is deprecated for new jobs once v2 ships and kept read-only for historical reference only; no data is migrated/backfilled into Notion. |

### FR-G — Kanban-Triggered Automation (new requirement, surfaced during scoping Q&A)
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-G1 | Moving a job's Kanban card to certain statuses automatically triggers the corresponding pipeline step, without Nicolas needing to separately ask Claude to run it. | At minimum: moving to `cv scored` triggers `cv-match`; moving to `cover letter done` triggers `write-outreach`; moving to `first interview` (or earlier, on `applied`) triggers `company-research` + `interview-prep` cheat-sheet generation if not already done. Exact status→skill mapping needs confirmation (see OQ-10). |
| FR-G2 | The trigger mechanism is an n8n workflow that polls the Notion database for status changes on a schedule, then invokes the relevant skill/agent. | Reuses the existing n8n instance already running the weekly scrape; no new hosted webhook service is introduced for v1. Poll frequency is configurable (recommendation: every 5–15 minutes — needs validation, OQ-11). |
| FR-G3 | Automated runs never auto-apply, auto-send, or auto-message — the existing hard rule applies to automatically-triggered work exactly as it does to conversationally-triggered work. | Automated pipeline steps produce/update drafts and Notion content only; any actual sending remains a manual, human action. |
| FR-G4 | If an automated step fails (e.g., a skill errors, a required input is missing), the card/job is flagged visibly in Notion rather than silently stuck. | A failed automated run adds a visible note/flag on the job's Notion page (e.g., a "needs attention" property or comment) so Nicolas notices without having to guess why nothing happened. |

### FR-E — Per-Job File Organization
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-E1 | The tailored CV for a job is attached as a native file on that job's Notion page. | File is uploaded to Notion, viewable/downloadable from the page, versioned if the CV is revised (OQ-5 on version handling). |
| FR-E2 | The cover letter for a job is attached as a native file on that job's Notion page. | Same standard as FR-E1. |
| FR-E3 | File naming/organization is consistent across jobs. | Naming convention proposed (recommendation, not yet confirmed): `{Company} - {Role} - CV.pdf` / `{Company} - {Role} - Cover Letter.pdf`. |

### FR-F — Interview Cheat Sheet (Notion)
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-F1 | A one-page interview cheat sheet is generated per job once it reaches (or is about to reach) an interview stage. | Cheat sheet contains: key stories, key metrics, talking points, questions to ask (FR-B2), and — new in v2 — a condensed pointer to the company research brief (FR-A). |
| FR-F2 | The cheat sheet is published to the job's Notion page for every job that reaches an interview stage, not gated by the current 9.3/10 auto-score threshold. **[RESOLVED]** | Threshold gating (`coach.auto_prep_min_score`) and the separate CV Coach cron pipeline are removed; cheat-sheet generation is triggered for every job (either conversationally or via the new FR-G n8n automation) once it reaches an interview stage. |

## 8. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Data integrity | No fabricated facts anywhere in generated content (company research, CV, cover letter, Q&A) — carries over the existing hard rule from CLAUDE.md verbatim. |
| Traceability | Every quantified claim in CV/cover letter/Q&A must trace to the CV or experience bank, as today. Every company research data point must cite its source and retrieval date. |
| Human control | No auto-apply, no auto-messaging, no auto-status-transition without an explicit request or explicit confirmation — carries over the existing hard rule. |
| Consistency | Company research, Q&A, cover letter, and cheat sheet generation should be triggerable both individually and as part of the existing `run-my-week` orchestration, without duplicating logic (reuse skills, don't fork them). |
| Auditability | Notion pages should retain enough history (or versioned file attachments) to see what CV/cover letter version was actually sent for a given application. |
| Recency | Company research data (news, headcount) should show a retrieval date so staleness is visible; no implicit freshness guarantee beyond that. |

## 9. User Experience Considerations

- Interaction model stays conversational, consistent with the rest of the repo (natural-language requests like "research Mistral for me," "give me interview questions for the Euronext role," "mark this as applied").
- The Notion Kanban board becomes the primary visual "where am I in my search" view, replacing the Google Sheet — this is a meaningful workflow change and should be validated with Nicolas using a mocked-up board structure before full build (see validation checklist).
- Each job's Notion page should be skimmable end-to-end: research brief → CV → cover letter → cheat sheet, top to bottom, since it now replaces both the local `applications/` folder and the Drive subfolder as the "one place" for that job.

## 10. Dependencies

- **Notion API access** — a Notion integration/token with permission to create databases, pages, and upload file attachments under the existing "Job Search" parent page (`coach.notion_parent_page_id`). **[RESOLVED: reuse existing parent page]** Both the Claude Code/Cowork session (for conversational runs) and the n8n instance (for FR-G polling/automation) need this token — this is a new dependency: n8n did not previously need Notion access, only Google Drive and Apify.
- **n8n Notion-polling workflow (new)** — a new n8n workflow that polls the Kanban database on a schedule and triggers skill execution on status change (FR-G). This requires n8n to be able to invoke Claude/skill execution, not just read/write data as it does today for the scrape — this is new automation surface area beyond what the current n8n workflow does, and needs its own technical design (OQ-11, OQ-12).
- **Web/news/video retrieval mechanism** for company research — **[RESOLVED: general web search/browsing, no new Apify actor for v1]**. Revisit a dedicated actor later only if search/browsing proves unreliable for headcount or YouTube lookups.
- **Existing skills** (`cv-match`, `write-outreach`, `interview-prep`, `find-opportunities`, `run-my-week`) as the logic base to extend, not replace.
- **CV source files** (`context/cv-master.md`, `context/cv-master-fr.md`) unchanged.
- **Deprecation dependency:** removing the Hermes-cron-based CV Coach (`scan-jobs`/`prep-application`) is itself a piece of work — it lives outside this repo in `~/.hermes/skills/cv-coach/` and needs to be explicitly decommissioned, not just left running unused.

## 11. Risks

| Risk | Impact | Mitigation (recommendation) |
|---|---|---|
| Open-position counts and headcount data are often inconsistent across sources (careers page vs. LinkedIn vs. Glassdoor) and can be stale or wrong. | Medium — could mislead prioritization or interview talking points. | Always cite source + retrieval date (FR-A4/A5); never present a single number as definitive without its source. |
| "Significant news" retrieval could surface irrelevant or low-quality results for smaller/private companies with little public coverage. | Medium | Allow explicit "no significant news found" as a valid output, consistent with the existing "never fabricate" rule. |
| Notion file attachment size/format limits could affect CV/cover letter uploads (e.g., large `.docx` exports). | Low–Medium | Validate Notion's file size limits during implementation; confirm target file formats (PDF vs. DOCX vs. Markdown). |
| Migrating the tracker from Google Sheets to Notion loses the existing conditional-formatting/follow-up-reminder logic (`tracker/job-tracker-model.md` has overdue/upcoming follow-up formulas). | Medium | Recreate equivalent views/reminders in Notion (e.g., a filtered view for overdue follow-ups) — needs explicit design, not automatic in Notion databases. |
| Running company research per job adds latency/cost (multiple searches per job) compared to the current lightweight `company-intel` mention in skill docs (which appears to be a "light pass," not deeply specified — no `company-intel/SKILL.md` file actually exists in the repo). | Medium | **[RESOLVED]** Confirmed as a genuinely new skill (`company-research`) to build; use general web search/browsing for v1, revisit dedicated actors if latency/quality is a problem. |
| Two coexisting "cheat sheet" mechanisms (the existing 9.3/10-gated CV Coach cron path and this PRD's for-every-interview path) could produce duplicate or conflicting Notion pages for the same job. | Medium | **[RESOLVED]** CV Coach is deprecated; only the new unified flow publishes cheat sheets going forward. Decommission the Hermes cron job explicitly (see Dependencies) so it can't fire a second time. |
| n8n polling Notion and triggering skill execution is new automation surface area — status changes could misfire (e.g., double-trigger on a flaky poll, or trigger on a status the mapping didn't intend), and n8n invoking Claude Code/skill execution is architecturally different from n8n's current role (pure data movement, no LLM invocation). | High | Needs explicit technical design before build: how does n8n invoke a skill (Claude API call, a webhook into a running Claude session, or something else)? Recommend an idempotency check (e.g., "already processed this status transition") before design finalizes (OQ-11, OQ-12). |
| A job could be moved backward or skipped between statuses (e.g., dragged straight from `selected` to `applied`), which may or may not be intended to still fire every intermediate step's automation. | Medium | Define the intended behavior for skipped/backward transitions explicitly during automation design (OQ-10). |

## 12. Rollout Considerations

- Recommend a phased rollout given this is a personal tool with an existing working pipeline:
  1. **Phase 1:** Build the Notion Kanban database (with full 9-status list, including terminal states) + per-job page template under the existing "Job Search" page, and wire it as the tracker for newly selected jobs, without yet touching file attachments, research, or automation (validates the Notion data model first). Google Sheet stays read-only, no backfill.
  2. **Phase 2:** Add native file attachments (final-version-only tailored CV, cover letter) to job pages, reusing existing `cv-match`/`write-outreach` output.
  3. **Phase 3:** Build the new `company-research` skill and attach briefs to job pages; wire it as the `company-intel` source for `write-outreach`/`run-my-week`.
  4. **Phase 4:** Extend the interview cheat sheet (with the tailored "questions to ask them" subsection) to every interview-stage job; decommission the Hermes CV Coach cron pipeline once this is live and verified.
  5. **Phase 5 (higher risk, build last):** Design and ship the n8n Notion-polling automation (FR-G) that triggers pipeline steps on card moves — sequenced last since it's the highest-risk/least-defined piece (see Risks) and benefits from Phases 1–4 already being stable and manually verified first.
- No hard cutover date implied; Nicolas can keep using the Google Sheet in parallel (read-only, historical) until Notion is trusted.

## 13. Success Metrics

No usage baseline is available from the repo (see Section 2.3), so metrics below are proposed candidates to confirm, not measured targets:
- 100% of jobs reaching `selected` status have a company research brief before a cover letter is drafted.
- 100% of jobs reaching `first interview` have a Notion cheat sheet (up from the current ~gated-to-9.3/10-only coverage).
- Zero jobs tracked outside the Notion board once v2 is adopted (i.e., Google Sheet fully superseded for new entries).
- Time-to-package (job selected → CV + cover letter + cheat sheet ready) — baseline currently unknown; recommend measuring after Phase 2 to set a target.

## 14. Open Questions

### Resolved during scoping Q&A (kept here for traceability)
| # | Question | Resolution |
|---|---|---|
| OQ-1 | Terminal states beyond the six listed statuses? | **Yes** — add `offer`, `rejected`, `withdrawn`. |
| OQ-2 | Does the existing cheat-sheet "Questions to ask them" satisfy the interviewer-question requirement? | **Yes**, kept as a cheat-sheet subsection, now tailored using the company research brief. |
| OQ-3 | What retrieval mechanism powers company research? | **General web search/browsing** for v1; no new Apify actor. |
| OQ-4 | Backfill historical data into Notion? | **No** — start fresh; Google Sheet stays read-only for history. |
| OQ-5 | Keep all CV/cover-letter refinement iterations in Notion, or final only? | **Final version only.** |
| OQ-7 | Is company research a net-new skill, and should it also cover the missing `company-intel` gap? | **Yes to both** — one new `company-research` skill serves both purposes. |
| OQ-8 | Deprecate, keep, or merge the existing CV Coach cron pipeline? | **Deprecate** — fold into the unified Notion-first flow. |
| OQ-9 | Where should the new Kanban database live? | Under the **existing "Job Search" parent page**. |

### Still open — need decisions before/during build
| # | Question | Why it matters |
|---|---|---|
| OQ-10 | Exact status→automation mapping for FR-G (which status transitions trigger which skill), and how backward/skipped transitions should behave (e.g., dragging a card straight from `selected` to `applied`). | Without a precise mapping, the automation could under-trigger (nothing happens) or over-trigger (duplicate runs) — this is the core spec of FR-G1 and needs to be nailed down before any n8n workflow is built. |
| OQ-11 | Technical design for how n8n actually invokes skill/agent execution on a detected status change (this is new: today n8n only moves data, it never calls an LLM/skill). Options include calling the Claude API directly from an n8n node (bypassing skills' Claude-Code-specific behavior like the refinement-loop subagent), or some other invocation path. Also: what poll interval is acceptable? | This is flagged as the highest-risk item in the Risks table — n8n-invoked runs may not get the same refinement-loop/subagent behavior that Claude Code sessions get today (per CLAUDE.md, subagent loops only run in Claude Code/Cowork; `app/server.py` already documents degrading to a single-pass fallback outside that environment — n8n-triggered runs would likely hit the same limitation). |
| OQ-12 | Credential/access model for n8n to reach both Notion (new) and whatever invokes Claude/skills — does this reuse the existing Apify/Drive credential pattern in n8n, or need a new credential type? | Needed before Phase 5 (automation) can be scoped or estimated. |
| OQ-13 | Target file format for the native Notion CV/cover-letter attachments (PDF export vs. Markdown vs. DOCX) — not yet decided. | Affects both `cv-match`/`write-outreach` output steps and Notion's file-upload handling. |
| OQ-14 | Recency window for "recent" YouTube video / "significant recent news" in the company research brief (e.g., last 12 months) — a placeholder recommendation was made in the original draft but not yet confirmed. | Avoids surfacing a video from years ago as if it were current signal. |

## 15. Assumptions

- Nicolas has (or can create) a Notion integration with API access and permission to write to his workspace, including the existing "Job Search" parent page — not yet confirmed with a tool call, since no Notion access is available in this session.
- The existing skill logic for CV scoring/tailoring, cover-letter drafting, and Q&A generation is being kept as-is; this PRD only changes *where output is filed* (Notion vs. Drive/Sheets), *adds* company research content, and *adds* an automation trigger layer — not a rewrite of proven skill logic.
- "Significant news in link with the job opportunities" means news about the *company* relevant to why they might be hiring or what the role involves (e.g., funding, expansion, product launch) — interpreted this way in FR-A6; confirm this matches intent.
- "Number of open positions in France and headquarter country" means a count of current job openings at that company, not open positions specifically matching Nicolas's target titles — confirm this interpretation.
- n8n has (or can be given) the technical ability to call Claude/skill execution, not just move data between Notion/Drive/Apify as it does today — this is assumed feasible but not yet validated (OQ-11); if it turns out n8n cannot reasonably invoke the full skill logic (especially the Claude-Code-only refinement loops), Phase 5 may need a different design (e.g., n8n only flags "ready to run" and Nicolas still triggers the actual skill conversationally).

---

## 16. Epic & User Stories

**Epic: Notion-Centric Job Application Workflow** — extend the existing cv-job-match pipeline so that once a job is selected, company research, interview prep, cover letter drafting, and pipeline tracking all converge into a single Notion-based system of record.

Traceability: each story references its PRD requirement ID(s).

| Story ID | Story | Priority | Acceptance Criteria | Dependencies | Technical Notes (recommendation) |
|---|---|---|---|---|---|
| US-1 | As Nicolas, I want a Notion database with a Kanban view and the exact status set I use (`selected`, `cv scored`, `cover letter done`, `applied`, `first interview`, `second interview`, + terminal states TBD), so that I can see my whole pipeline at a glance in one tool. | P0 | FR-D1, FR-D2. A card exists per pursued job; statuses match confirmed list (pending OQ-1); board view groups by status. | OQ-1, OQ-9 (parent page), Notion API access (OQ-6) | Recommend building as a Notion database with a `select`/`status` property type for native Kanban grouping. |
| US-2 | As Nicolas, I want each Kanban card to open a full job page with research, CV, cover letter, and cheat sheet in one place, so that I never have to hop between Drive, local folders, and a spreadsheet. | P0 | FR-D3. Opening any card shows all five content sections (job details, research, CV, cover letter, cheat sheet), even if some are empty pending later stages. | US-1 | Recommend a Notion page template applied on card creation. |
| US-3 | As Nicolas, I want to update a job's status by asking in plain language (e.g., "mark Mistral as applied"), so that tracking doesn't require manually clicking through Notion. | P1 | FR-D4. A natural-language status request updates the correct card's status property with no other fields altered unintentionally. | US-1 | Consistent with existing conversational config-edit pattern in README. |
| US-4 | As Nicolas, I want a company research brief (website summary, recent YouTube video, open positions in France, open positions in HQ country, relevant recent news) generated for any selected job, so that I can prep and decide without manually searching multiple sources. | P0 | FR-A1–A6. Brief includes all five elements or an explicit "not found" for any missing one, each cited with source + date. | OQ-3 (retrieval mechanism), OQ-7 (confirm net-new skill) | Recommend building as a new skill (working name `company-research`) rather than extending the undocumented `company-intel` reference. |
| US-5 | As Nicolas, I want the company research brief attached to the job's Notion page, so that it's part of the single source of truth for that application. | P0 | FR-A7. Brief appears as a Notion section on the job page after generation, without manual copy-paste. | US-2, US-4 | |
| US-6 | As Nicolas, I want a cover letter tailored to the job description, reusing the existing quality/refinement logic, so that outreach quality doesn't regress during the rebuild. | P0 | FR-C1, FR-C2. Output structure and quality bar match current `write-outreach` skill behavior. | Existing `write-outreach` skill (unchanged) | Reuse skill logic; only change the output destination. |
| US-7 | As Nicolas, I want the final cover letter and tailored CV attached as native files on the job's Notion page, so that everything I need to apply lives in one place. | P0 | FR-C3, FR-E1, FR-E2, FR-E3. Files appear as downloadable attachments on the job page with a consistent naming convention. | US-2, US-6, existing `cv-match` output | Confirm target file format (PDF export vs. Markdown) — OQ not yet raised, flag during implementation. |
| US-8 | As Nicolas, I want interview Q&A generated for a job (reusing existing `interview-prep` logic), so that I'm prepared for what I'll be asked. | P0 | FR-B1. Output structure matches current skill (strengths/weaknesses, "tell me about yourself," behavioral questions), grounded in CV facts only. | Existing `interview-prep` skill (unchanged) | |
| US-9 | As Nicolas, I want a clearly separated list of sharp questions to ask the interviewer, tailored using the company research brief, so that I can demonstrate insight rather than asking generic questions. | P1 | FR-B2. At least 4–5 questions, each referencing a specific fact from the research brief or JD. | US-4 (research brief must exist first), OQ-2 | |
| US-10 | As Nicolas, I want a one-page interview cheat sheet published to Notion for every job reaching an interview stage — not just the top-scoring ones — so that I always walk in prepared. | P0 | FR-F1, FR-F2. Cheat sheet generated and attached for any job at `first interview` status or later, regardless of Fit Score. | US-2, US-4, US-8, US-9, OQ-8 (decide relationship to existing CV Coach) | Recommend explicitly removing/bypassing the `coach.auto_prep_min_score` gate for this manually-triggered path. |
| US-11 | As Nicolas, I want the new Notion tracker to fully replace the Google Sheet for new jobs, so that I have one tracking system instead of two. | P1 | FR-D5. All newly selected jobs from ship date onward are tracked only in Notion; Google Sheet is not updated for new entries; no historical backfill performed. | US-1 | |
| US-12 | As Nicolas, I want moving a job's Kanban card to a new status to automatically trigger the next piece of work (e.g., moving to `cv scored` runs `cv-match`), so that I don't have to separately ask Claude to do it every time. | P2 (build last — see Rollout Phase 5) | FR-G1–G4. A card moved to a mapped status triggers the correct skill within the agreed poll interval; failures are visibly flagged on the job's Notion page rather than silent; no automated step ever sends/applies anything. | US-1 through US-10 (needs the underlying skills and Notion structure working first), OQ-10, OQ-11, OQ-12 | Recommend building as a new n8n workflow that polls the Notion database (reusing existing n8n credentials pattern), with an idempotency check per status transition to avoid double-triggering. Explicitly out of the loop: whatever "refinement subagent" behavior is Claude-Code-session-specific may not be available when n8n triggers a skill — confirm expected quality/behavior with Nicolas before this ships (OQ-11). |

---

## Validation Checklist (for Nicolas to confirm before implementation starts)

**Resolved this session (OQ-1 through OQ-9) — captured above, re-confirm only if anything reads wrong:**
- [x] Kanban status list finalized: `selected, cv scored, cover letter done, applied, first interview, second interview, offer, rejected, withdrawn`.
- [x] Interviewer questions stay inside the existing cheat sheet, tailored with the research brief.
- [x] Company research uses general web search/browsing for v1.
- [x] No backfill of historical Google Sheet / `applications/` data into Notion.
- [x] Notion keeps final CV/cover-letter versions only.
- [x] One new `company-research` skill covers both the research brief and the `company-intel` gap.
- [x] Existing CV Coach cron pipeline is deprecated in favor of the unified flow.
- [x] New Kanban database lives under the existing "Job Search" Notion parent page.

**Still open — confirm before/during build:**
- [ ] Nail down the exact status→automation mapping and backward/skipped-transition behavior for the n8n trigger (**OQ-10**).
- [ ] Decide the technical mechanism for n8n to invoke skill/agent execution, and accept/adjust the expectation that Claude-Code-only refinement-loop behavior may not carry over to n8n-triggered runs (**OQ-11**).
- [ ] Confirm n8n's credential/access model for reaching Notion and triggering Claude/skill execution (**OQ-12**).
- [ ] Confirm target file format for native Notion CV/cover-letter attachments — PDF, Markdown, or DOCX (**OQ-13**).
- [ ] Confirm the recency window for "recent" YouTube videos and "significant recent news" in the research brief (**OQ-14**).
- [ ] Review and confirm/adjust the proposed priorities (P0/P1/P2) in the story table, especially US-12's "build last" sequencing given it's the highest-risk, least-defined piece.
- [ ] Decommission plan for the Hermes-hosted CV Coach cron job once the new flow is verified live (see Dependencies).
