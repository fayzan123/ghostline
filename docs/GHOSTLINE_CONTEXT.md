# Ghostline — Product Context

> This document is intended as context for AI assistants (resume updates, portfolio pages, project writeups, etc.). It explains what Ghostline is, why it was built, and how it works technically.

---

## What Is Ghostline?

Ghostline is an automated lead generation and outreach pipeline built by Fayzan Malik and Dilraj (co-founders of Chox). It discovers software developers on GitHub who are actively building AI agents that call real-world APIs, qualifies and scores them as potential customers for Chox, exports them to a Google Sheet, and enables personalized cold email outreach with human review before any email is sent.

The name "Ghostline" reflects the idea of a silent, automated system operating in the background — surfacing leads without the founders having to manually hunt for them.

---

## Why It Was Built

Chox is an AI agent governance layer. It sits between an AI agent and the external APIs it calls (Stripe, Twilio, databases, etc.) and enforces policies on what the agent is allowed to do at runtime. The ideal Chox customer is a developer who is already using a framework like LangChain or LangGraph to build agents that make real, consequential API calls.

The challenge: there is no directory of such developers. They exist scattered across GitHub, quietly building production-grade agent pipelines. Ghostline was built to find them programmatically — searching GitHub at scale, filtering out tutorials and toy projects, scoring each lead on signals of production intent, and connecting them to Chox through personalized outreach.

Ghostline is Chox's go-to-market engine.

---

## High-Level Architecture

Ghostline operates as two independent pipelines that share a Google Sheet as their data layer:

```
[GitHub] → Discovery Pipeline → [Google Sheet] → Outreach Pipeline → [Email Sent]
```

### Pipeline 1: Lead Discovery (automated, runs daily)

Searches GitHub for repositories matching patterns like LangGraph + Stripe, LangChain + PostgreSQL, CrewAI + Twilio, etc. Filters out forks, tutorials, and low-signal repos. Extracts developer emails. Scores each lead on a 0–100 scale. Writes new qualified leads to Google Sheets.

### Pipeline 2: Outreach Agent (human-in-the-loop, run manually)

Reads uncontacted leads from the sheet. Fetches each repo's README from GitHub. Uses Claude (Anthropic) to generate a personalized 150-word cold email for each lead. Presents every email for human review in a terminal UI — the founder approves, rejects, or edits each one before anything is sent. Sends approved emails via SMTP and records the contact event back to the sheet.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Lead discovery | GitHub REST API (authenticated, paginated) |
| Lead storage | Google Sheets API (via service account) |
| Outreach workflow | LangGraph (state graph with SQLite checkpointing) |
| Email generation | Anthropic Claude (Sonnet for email, Haiku for scoring) |
| Email sending | Gmail SMTP (app password) |
| State persistence | SQLite (`ghostline_outreach.db`) |
| Scheduling | cron (daily at 6 AM) |

---

## Lead Discovery Pipeline — Step by Step

### 1. GitHub Search

Ghostline runs 16 targeted search queries against the GitHub API:

- `langgraph stripe language:python fork:false`
- `langchain postgresql language:python fork:false`
- `langgraph ToolNode language:python fork:false`
- `crewai stripe language:python fork:false`
- ... and 12 more

Each query fetches up to 10 pages of 100 results. Results are deduplicated by repository full name.

### 2. Qualification Filtering

Repos are filtered to remove:
- Official framework repos (langchain-ai, deeplearning-ai, Microsoft, etc.)
- Tutorial/demo repos (name or description contains: tutorial, example, demo, course, homework, etc.)
- Jupyter Notebook primary language (usually notebooks = tutorials)
- Repos with 0 stars + no description + no topics (likely throwaway)

### 3. Email Extraction

For each unique repo owner not already in the sheet, Ghostline attempts email extraction using a 4-method fallback chain:

1. **GitHub profile** — check the `email` field directly
2. **Commit metadata** — parse author/committer email from recent commits
3. **Public events** — parse push event commit data
4. **Bio regex** — search the profile bio for an email pattern

Emails from `@users.noreply.github.com`, `noreply@`, and similar are rejected. If multiple emails are found, non-freemail (corporate/personal domain) is preferred over freemail (gmail, yahoo, etc.).

### 4. Enrichment

Each lead is enriched with data from the GitHub API:
- Full name, bio, company, location, blog URL, Twitter handle
- Follower count, public repo count
- Repo stars, language, topics
- Frameworks detected (langchain, langgraph, crewai, autogen)
- Risk APIs detected in repo metadata (stripe, twilio, sqlalchemy, boto3, etc.)

### 5. Lead Scoring (0–100)

Scores are calculated across four dimensions:

| Dimension | Max Points | Signals |
|-----------|-----------|---------|
| **Tool Use** | 35 | Tool-calling imports (5 pts ea), stateful graph imports (3 pts ea), risk API imports (5 pts ea) |
| **Production Maturity** | 30 | Production keywords in description/README, repo age, README quality |
| **Social Proof** | 20 | Stars (up to 11 pts), contributor count (up to 9 pts) |
| **Developer Profile** | 15 | Has org/company (5 pts), recent commit frequency, follower count |

**Tier 1:** score ≥ 20 — production-grade, ready for outreach
**Tier 2:** score ≥ 5 — worth tracking, not yet ready
**Disqualified:** score < 5 — dropped from pipeline

### 6. Pain Point Inference

Each lead is assigned one inferred pain point category based on their tech stack:

- `financial_risk` — Stripe, Plaid, Square, PayPal
- `data_mutation_risk` — SQLAlchemy, Boto3, Psycopg2, PyMongo
- `communication_risk` — Twilio, SendGrid, Slack
- `governance_at_scale` — 3+ contributors + LangGraph/CrewAI/AutoGen
- `blind_tool_calls` — default (no specific signals)

### 7. Write to Sheet

New leads are batch-appended to Google Sheets. Each row has 28 columns including: `github_username`, `email`, `repo_url`, `lead_score`, `lead_tier`, `inferred_pain_point`, `risk_apis_detected`, `contacted`, and more.

---

## Outreach Pipeline — Step by Step

The outreach pipeline is a LangGraph `StateGraph` with 8 nodes and a human-in-the-loop interrupt before any email is sent.

### The Graph

```
load_leads → fetch_readmes → generate_emails → present_for_review
  ↕ [INTERRUPT — human reviews here]
process_approval → send_emails → update_sheet → report
```

### Node Details

**`load_leads`** — Reads uncontacted leads from the Google Sheet. Slices to a configurable batch size (default: 10).

**`fetch_readmes`** — For each lead's repo, fetches the README from GitHub (up to 2000 characters). Gracefully handles 404s — if no README, email generation proceeds with just the repo metadata.

**`generate_emails`** — Calls Claude Sonnet to generate a personalized 150-word cold email for each lead. The prompt provides:
- Chox product context (loaded from `docs/CHOX_CONTEXT.md`)
- The lead's repo name, description, and README
- The frameworks and risk APIs detected
- Strict constraints: plain text, no markdown, no em-dashes, no bullet points, max 150 words

**`present_for_review`** — Signals the human interrupt. After this node, execution pauses.

**[Human Review Terminal]** — A raw-mode terminal UI (`review_cli.py`) shows each draft one at a time:
```
Lead: Alice Developer (alice@example.com)
Repo: alice-org/agent-framework — LangGraph + Stripe, 45 stars
README: [first 500 chars]

Subject: Autonomy needs guardrails

Hi Alice,

I noticed you're building agent-framework...

ACTION: [A]pprove / [R]eject / [E]dit / approve [B]atch / [Q]uit
```

Controls: `A` approve, `R` reject, `E` edit in `$EDITOR`, `B` bulk approve all remaining, `Q` quit and save checkpoint.

**`process_approval`** — Applies the human's decisions to each draft: approved, rejected, or edited with a new body.

**`send_emails`** — Sends approved/edited drafts via Gmail SMTP. Randomizes a 90–180 second delay between each send to avoid spam filters. Respects a daily send limit (`MAX_EMAILS_PER_DAY`).

**`update_sheet`** — For each sent email, marks `contacted = TRUE`, writes `contacted_at` timestamp and `contact_method = email` back to the sheet.

**`report`** — Prints a final summary: sent count, failed count, rejected count, duration.

### Resumable Runs

LangGraph automatically checkpoints state to `ghostline_outreach.db` (SQLite). If the session is interrupted — either by the user pressing `Q` during review, or by a crash — the run can be resumed with `--resume`. This reloads the full graph state (including already-generated emails) and picks up from the approval step without re-calling Claude or re-fetching READMEs.

---

## Email Generation Details

Emails are generated by Claude Sonnet at temperature 0.7 with the following constraints:

- **Length:** 150 words maximum
- **Format:** Plain text, no markdown, no bullet points, no em-dashes
- **Structure:** 3 paragraphs + sign-off
  - Paragraph 1: Reference their specific project and what it does
  - Paragraph 2: Connect their use case to Chox's governance value proposition
  - Paragraph 3: Invite them to try Chox
- **Sign-off:** Fixed — "Fayzan & Dilraj, Co-founders, Chox (chox.ai)"
- **Personalization inputs:** Repo name, description, README content, detected APIs and frameworks

Retry logic handles Anthropic rate limits (exponential backoff: 2s → 4s → 8s).

---

## Key Design Decisions

**Metadata scoring over code analysis** — Scoring uses repo metadata (description, stars, topics, import keywords visible in README) rather than downloading and parsing every file. This keeps GitHub API usage within rate limits while still capturing strong signals.

**4-method email extraction chain** — Email addresses are sourced from wherever they can be found, in priority order. This achieves higher extraction rates than relying solely on the GitHub profile email field, which many developers leave blank.

**LangGraph for outreach workflow** — Using a state graph enables clean separation of concerns (each node does one thing), built-in checkpointing for resume, and an explicit interrupt point for human review. The SQLite checkpoint store means nothing is lost if the session is interrupted mid-review.

**Human-in-the-loop by default** — No email is ever sent without founder review. This preserves quality and prevents sending to miscategorized leads.

**Dual Claude model strategy** — Claude Sonnet for email generation (best quality at reasonable cost), Claude Haiku for supplementary ICP scoring (cheaper, sufficient for classification tasks).

---

## Project Structure

```
ghostline/
├── run.py                     # Discovery pipeline entry point
├── run_outreach.py            # Outreach agent entry point
├── score_leads.py             # Supplementary: Claude-based ICP scoring
├── discovery/
│   ├── discover.py            # GitHub search + pagination
│   ├── qualify.py             # Repo filtering
│   ├── extract_email.py       # 4-method email extraction
│   ├── score.py               # Lead scoring + tier + pain point
│   └── github_client.py       # GitHub REST API wrapper
├── outreach/
│   ├── outreach_graph.py      # LangGraph state graph (8 nodes)
│   ├── outreach_state.py      # State schema (TypedDict)
│   ├── outreach_config.py     # Configuration constants
│   ├── email_generator.py     # Claude email generation
│   ├── readme_fetcher.py      # GitHub README fetching
│   ├── review_cli.py          # Terminal review UI
│   ├── outreach_sheets.py     # Sheet read/write for outreach
│   └── outreach_emails.py     # SMTP sending logic
├── shared/
│   ├── config.py              # Global constants, blocklists, thresholds
│   ├── models.py              # Lead dataclass
│   ├── sheets.py              # Google Sheets API integration
│   └── report.py              # Run summary reporting
├── docs/
│   ├── CHOX_CONTEXT.md        # Product context injected into Claude prompts
│   └── OUTREACH_AGENT_PLAN.md # Design spec
├── ghostline_outreach.db      # SQLite checkpoints (LangGraph)
├── runs.log                   # Historical run summaries
└── cron.txt                   # Daily cron schedule
```

---

## Metrics & Scale

- **Daily discovery:** ~150 repos searched, ~45 qualified, ~32 new leads added to sheet per run
- **Email extraction rate:** ~92% of qualified leads yield a valid email
- **Tier 1 rate:** ~25% of leads score ≥ 20
- **Outreach batch size:** 10 emails per manual run
- **Daily send cap:** 20 emails (ramps up over time for deliverability)
- **GitHub API usage:** ~500 core API calls per discovery run (of 5000/hr limit)

---

## Builder

Built by **Fayzan Malik**, co-founder of Chox (chox.ai). Chox is an AI agent governance platform — it intercepts and governs tool calls made by AI agents before they execute, applying configurable policies to prevent data leaks, unauthorized mutations, and runaway agent behavior.

Ghostline was built from scratch as a sales infrastructure project — no third-party lead gen tools, no scrapers, no data vendors. It runs on GitHub's public search API, respects rate limits, and generates outreach that is personalized from the lead's actual code.