# Ghostline SaaS -- Business & Technical Plan

## 1. Executive Summary

Ghostline is a GitHub-native lead generation and AI-powered outreach platform for B2B companies selling to developers. The pipeline -- discover, qualify, score for fit, personalize, review, send, write-back -- is proven and running in production. The SaaS transformation generalizes this pipeline so any company can describe their product and ideal customer, and Ghostline handles the rest: AI generates the GitHub search queries, AI generates a fit scoring rubric, the discovery engine finds developers building things relevant to the client's product, only developers scoring 3+ on fit get outreach, and every email references the developer's actual project.

**Two-sentence pitch**: "Describe your product and who you want to reach. Ghostline finds developers on GitHub who can actually use it, and sends them personalized emails referencing what they're building."

**Goal**: $10k/month MRR within 9 months of first paying client.

**Core differentiators**:
1. **AI-powered fit scoring** -- Every lead is evaluated against a client-specific rubric before outreach. "We only email developers who can actually use your product." No other outreach tool does this.
2. **AI-powered query generation** -- Clients describe their product and ICP in plain English. AI generates optimized GitHub search queries. Clients never touch search syntax.
3. **GitHub-native discovery** -- Finds developers by what they are actively building right now, not by job title or LinkedIn profile. No other SMB-priced tool does this end-to-end.

---

## 2. Target Customer & Market

### Who Uses Ghostline

**Primary customer**: Any B2B company selling a product that developers integrate into their projects. This includes:

- **Dev tools & SDKs** -- testing frameworks, CI/CD tools, code quality platforms
- **APIs & infrastructure** -- payment APIs, messaging APIs, auth providers, databases
- **Cloud & platform services** -- hosting, serverless, monitoring, logging
- **Security products** -- vulnerability scanning, secrets management, agent governance
- **Data & AI infrastructure** -- vector databases, model hosting, feature stores, observability
- **Open-source companies** -- any OSS project with a commercial offering (the majority of modern dev tools)

**The common thread**: These companies have a product that shows up in code. If a developer uses their product, evidence of that usage appears in GitHub repositories -- imports, API calls, config files, SDK references. That is what makes GitHub-native discovery work.

**Who Ghostline does NOT serve well**: Companies selling to non-technical buyers (marketing SaaS, HR tools), companies whose product leaves no code-level footprint (consulting, design tools), and enterprise sales teams with deal sizes above $50k/year who need account-based marketing, not volume outreach.

**Decision**: The target market is "any B2B company selling to developers" rather than narrowing to "dev tool companies" alone. The GitHub discovery model works for any product that leaves a code-level footprint. A payments API (Stripe competitor), a database (Supabase competitor), or a security scanner (Snyk competitor) all benefit equally. Narrowing to "dev tools" would exclude some of the highest-value customers. The broader framing also makes Ghostline's TAM significantly larger without requiring any architectural changes.

### Market Size

The lead generation software market is $7.4B in 2025, growing to $16.2B by 2034 (9.1% CAGR). The sales intelligence market is $4.85B in 2025, projected at $10.25B by 2032. Developer tooling specifically is a $6.4-7.6B market growing at 16% CAGR, with 550+ devtool companies mapped in the 2025 DevTools Landscape report. GitHub itself reported 130M+ active developers as of 2025.

**Conservative SAM for GitHub-native outreach**: 5,000-15,000 B2B companies selling developer-facing products, paying $300-$600/month, yields a $18M-$108M/year serviceable market. The category is nascent with no dominant SMB player.

### Direct Competitors (GitHub-Native)

**Reo.dev** -- Raised $4M seed in October 2025. Tracks 625M+ developer activity signals including GitHub interactions, package installs, and open-source telemetry. Customers include LangChain, N8N, Chainguard. However, Reo.dev is a signal intelligence layer, not an outreach tool. It identifies who is showing intent but does not automate personalized cold campaigns. It also requires companies to have existing product adoption to analyze -- targeting companies with traction, not companies seeking net-new leads. Pricing is custom and enterprise-oriented.

**Common Room** -- Signal intelligence with 50+ source integrations including GitHub. Contracts start at $15,000/year ($1,000-6,500/month). Community-first, not outbound-first. Completely out of reach for pre-Series A startups.

**No known tool** combines all four of: (1) GitHub as a primary lead source, (2) AI-powered fit scoring before any outreach, (3) AI-personalized emails referencing real technical context, and (4) SMB-accessible pricing. This is the gap Ghostline fills.

### Adjacent Competitors (Outreach Tools Without GitHub)

| Tool | GitHub signals | Fit scoring | Outreach automation | SMB pricing |
|---|---|---|---|---|
| Apollo.io ($49-99/user/mo) | No | No | Yes | Yes |
| Hunter.io ($34+/mo) | No | No | No | Yes |
| Lemlist ($69+/user/mo) | No | No | Yes | Yes |
| Instantly.ai ($37-97/mo) | No | No | Yes | Yes |
| Outreach.io ($100-160/user/mo) | No | No | Yes | No |
| Common Room ($1,000+/mo) | Yes (signal only) | Partial | No | No |
| Reo.dev (custom pricing) | Yes (signal only) | Partial | No | Partial |

**Key weakness shared by all**: None of them score leads for product-market fit before sending. They find contacts and blast emails. Ghostline's fit scoring system means clients only email developers who can actually use their product, which is why reply rates will be structurally higher.

---

## 3. The Generalized Product -- End-to-End Flow

### Step 1: Client Provides Product Context

The client fills out a self-serve onboarding form in the dashboard with these fields:

1. **Product name** -- e.g., "Chox"
2. **One-paragraph product description** -- What it does, who it's for, how developers integrate it. This becomes the seed for everything AI generates.
3. **Integration method** -- How does a developer use this product in code? SDK import, API call, config file, CLI tool, GitHub Action? Examples of what it looks like in code (e.g., `from chox import ChoxGuard`, `stripe.Charge.create`).
4. **Target developer profile** -- Free-text description of who should receive outreach. E.g., "Developers building AI agents with LangGraph or LangChain that call external APIs like Stripe, Twilio, or databases."
5. **What makes a developer a good fit** -- What should be true about their project for the product to be useful? What makes a developer a bad fit? E.g., "Good fit: agent calls external APIs with side effects. Bad fit: pure RAG pipelines with no tool calls."
6. **Competitor/overlap products** -- Products that are direct competitors or that the client does NOT want to target. These become blocklist entries.
7. **Sender identity** -- Name, reply-to email address, company, sign-off line, CTA preference (e.g., "reply to this email" vs. "try our free tier"). Ghostline handles the actual email sending infrastructure -- clients just provide the reply-to address where responses should land.

That is 7 fields. No unnecessary information. Every field feeds directly into query generation, rubric generation, or email generation. Nothing is collected that the system does not use. Notably absent: no SMTP credentials (Ghostline owns the sending infrastructure via Amazon SES), no GitHub token (Ghostline uses a managed PAT pool), no Google Sheets setup (Postgres + dashboard is the data layer).

### Step 2: AI Generates Search Queries

Given the product description, integration method, and target developer profile, Claude generates 10-20 optimized GitHub search queries. The AI understands GitHub search syntax -- it knows how to combine framework keywords with API references, how to use `pushed:>` date filters, how to exclude forks, how to target specific languages.

Example: For Chox (AI agent governance), AI would generate:
```
langgraph stripe language:python pushed:>2026-02-21 fork:false
langchain twilio language:python pushed:>2026-02-21 fork:false
crewai tool language:python pushed:>2026-02-21 fork:false
```

The client sees a preview of these queries and the first 10 repos they return. They can approve, edit, or request changes. After approval, queries are locked into their config.

### Step 3: AI Generates Fit Scoring Rubric

Given the product description and "what makes a good/bad fit" inputs, Claude generates a scoring rubric (the `SYSTEM_PROMPT` used in `score_leads.py`). This rubric is a detailed prompt that tells the scoring LLM exactly how to evaluate each lead for this specific client.

The rubric includes:
- How the product works and what integration looks like
- The critical implementation requirement (what must be true for a developer to use this product)
- Strong fit signals (raise score)
- Poor fit signals (lower score)
- 1-5 scoring scale with concrete definitions for each level

This rubric is stored as `scoring_rubric` in the client's config. It is used every time a lead is scored.

### Step 4: AI Generates Email Template Context

Given the product description, sender identity, and CTA preference, Claude generates the email system prompt -- the equivalent of the current `_SYSTEM_PROMPT` in `email_generator.py`. This includes:
- Product context (what to say about the client's product)
- Email structure and constraints
- Tone guidelines
- Sign-off and footer
- Banned words and patterns

The client reviews and approves this prompt. It becomes `email_context_doc` in their config.

### Step 5: Discovery Pipeline Runs Daily

The scheduler triggers the client's pipeline. For each search query:
1. GitHub search API returns matching repos
2. Repos are deduplicated and filtered (blocklists, forks, tutorials)
3. For each repo owner: profile is fetched, email is extracted (profile, commits, events)
4. Lead data is assembled and written to storage

### Step 6: Fit Scoring Runs on New Leads

For each new lead:
1. README is fetched (up to 3000 chars for scoring)
2. Lead data + README is sent to Claude Haiku with the client's scoring rubric
3. Claude returns a 1-5 score with one-sentence reasoning
4. Score and reason are written back to the lead record

**Only leads scoring 3+ proceed to outreach.** Leads scoring 1-2 are kept in the database (the client can see them) but never emailed. This is the core quality guarantee.

### Step 7: Outreach Pipeline Runs on Qualified Leads

For each lead scoring 3+:
1. README is fetched (up to 2000 chars for email context)
2. Lead data + README is sent to Claude Sonnet with the client's email system prompt
3. Claude generates a personalized email referencing the developer's actual project
4. **Content safety filter** screens the generated email: checks for external links to non-client domains, credential requests, urgency/scarcity language, impersonation, or phishing patterns. Flagged emails are held for manual review rather than queued.
5. Clean emails appear in the client's dashboard review queue. **Default behavior: emails auto-send after 24 hours unless the client rejects them.** The auto-send task checks email status at send time (not schedule time) to prevent race conditions — if a client rejects an email at hour 23, it will not send. Clients who want a hands-off experience get exactly that, while cautious clients can review before anything goes out.
6. Emails are sent via Ghostline's managed sending infrastructure (Amazon SES) from `send.ghostline.ai` with the client's reply-to address. SPF/DKIM/DMARC are configured once on Ghostline's domain — clients never touch DNS or SMTP settings.

### Step 8: Results Written Back

- Lead status updated in Postgres
- Pipeline run stats recorded in `pipeline_runs` table (repos found, leads scored, emails sent)
- **Zero-result alert check**: if any pipeline stage produced 0 output (0 repos, 0 qualified leads, 0 emails), send the client an email with specific, actionable guidance (e.g., "Your queries returned 0 results this week. Try broadening your target profile in Settings.")
- CSV export available in dashboard for clients who want spreadsheet data

---

## 4. Onboarding Flow (Fully Self-Serve)

The entire onboarding is automated. No calls, no manual setup, no Ghostline team involvement. The client signs up and the system handles everything.

### Self-Serve Onboarding Steps

1. **Stripe Checkout** -- Client selects a plan and enters payment info. Stripe creates the subscription.
2. **Magic link auth** -- Client receives a login link via email (Clerk). Lands in the dashboard.
3. **Product context form** -- The 7 fields from Section 3, Step 1. Clean, guided form with placeholder examples for each field. Tooltips explain what each field is used for. This is the only manual input the client ever provides. Form state is saved to localStorage so progress is not lost if the client navigates away.
4. **AI generation preview** -- System immediately generates:
   - Search queries (10-20)
   - Fit scoring rubric
   - Sample email system prompt

   All three are shown in a preview screen. The client can review and optionally edit any of them, or accept the defaults. Most clients will accept defaults -- the AI generation is good enough. A "Regenerate" button is available (rate-limited to 1 per 30 seconds to prevent abuse).
5. **Dry run** -- System discovers 10 repos using the generated queries, scores 5 leads, generates 2 sample emails. **This runs asynchronously with SSE progress updates** ("Searching GitHub... Found 10 repos... Scoring lead 1/5... Generating email 1/2...") so the client sees real-time progress instead of staring at a spinner. If the dry run returns 0 results, the system shows specific guidance ("Your queries may be too narrow — try broadening your target profile").
6. **Go live** -- Client clicks "Start Pipeline". First discovery run begins within 1 hour. Warm-up schedule starts automatically. No SMTP setup, no GitHub tokens, no Google Sheets — Ghostline handles all infrastructure.

**Total time from signup to live pipeline: ~15 minutes.**

No onboarding calls. No manual client config by Ghostline. No waiting for approval from the Ghostline team. The client is in control from start to finish.

### Automated Retention

- **Weekly digest email with "Lead of the Week"**: Automated email showing last week's pipeline stats -- leads discovered, leads scored 3+, emails sent, reply rate (once tracking is in place). Highlights the single highest-scoring lead with their repo name, what they're building, and why they're a great fit. Makes the digest worth opening. Sent every Monday morning.
- **Zero-result alerts**: Automated email after any pipeline run that produces 0 output at any stage, with specific actionable guidance: "Your queries returned 0 results — try broadening your target profile" or "All leads scored below 3 — consider adjusting your fit criteria." Sent immediately, not batched.
- **Smart alerts**: Email notification if pipeline encounters infrastructure errors (SES send failure, GitHub rate limit exhaustion, Postgres connection issues). Separate from zero-result alerts — these indicate system problems, not config problems.
- **Usage warnings**: Email when approaching plan limits (80% of leads/month, 80% of emails/month) with upgrade CTA.
- **Bounce/spam auto-pause**: If weekly bounce rate exceeds 5% or spam complaint rate exceeds 0.1%, the client's pipeline is auto-paused with an email explaining why and how to fix it.

---

## 5. AI Query Engine

### How It Works

The query generation system takes three inputs from the client:
1. Product description (what the product does)
2. Integration method (what it looks like in code)
3. Target developer profile (who should get outreach)

These are sent to Claude with a metaprompt that instructs it to generate GitHub search queries. The metaprompt encodes knowledge of GitHub search syntax, best practices, and common patterns.

### The Metaprompt (Stored Centrally, Not Per-Client)

```
You are a GitHub search query specialist. Given a product description, integration
method, and target developer profile, generate 10-20 GitHub search queries that will
find developers who could use this product.

GITHUB SEARCH SYNTAX RULES:
- Use "pushed:>{date}" to find recently active repos (last 30 days)
- Use "fork:false" to exclude forks
- Use "language:{lang}" to target specific languages
- Combine framework keywords with API/library keywords
- Use quoted strings for exact import patterns: "from stripe import"
- Use + to combine terms: langchain+stripe

QUERY DESIGN PRINCIPLES:
- Start with the highest-signal combinations: the client's target framework + the
  client's product or competing/complementary products
- Include queries for the client's product name itself (find existing users)
- Include queries for competing/complementary products (find potential switchers)
- Include queries for the underlying patterns the product addresses (find developers
  with the problem even if they haven't found a solution)
- Cover the primary programming language and secondary languages if applicable
- Aim for queries that return 50-500 repos each (too broad = noise, too narrow = no results)

OUTPUT FORMAT:
Return a JSON array of query strings. No explanations, just the queries.
```

### Query Optimization Loop

After initial generation, Ghostline tests each query against the GitHub search API (search only, no lead extraction) and reports back:
- Total results count per query
- Sample of 5 repo names/descriptions per query

Queries returning 0 results are dropped. Queries returning 10,000+ results are narrowed. This happens automatically during the onboarding preview step.

### Query Refresh

Queries use `pushed:>{SINCE_DATE}` where `SINCE_DATE` is recalculated on each run (30 days ago). No manual date updates needed. Quarterly, the system can re-run query generation with the client's updated product context to catch new frameworks or patterns that have emerged.

---

## 6. Fit Scoring System

This is Ghostline's most important differentiator. It is the reason clients will pay a premium over generic outreach tools, and the reason reply rates will be structurally higher.

### How It Works Today (score_leads.py)

The current system, built for Chox:
1. Reads all leads from Google Sheet
2. For each unscored lead, fetches the repo README (up to 3000 chars)
3. Sends lead data + README to Claude Haiku with a hardcoded Chox-specific rubric
4. Claude returns a 1-5 score with one-sentence reasoning
5. Score and reason are written back to the sheet

### How It Works in the SaaS Version

The system is identical in mechanics but generalized:
1. The rubric (`SYSTEM_PROMPT` in `score_leads.py`) becomes **per-client**, stored as `scoring_rubric` in `client_configs`
2. The rubric is **AI-generated** from the client's product description and fit criteria during onboarding
3. Scoring runs **automatically** after discovery, as part of the daily pipeline
4. Only leads scoring **3+ proceed to outreach**. This threshold is fixed -- not client-configurable. The whole point is quality control. If a client wants to lower the bar, they should adjust their rubric, not the threshold.

### AI Rubric Generation

Given a client's product description and good/bad fit criteria, Claude generates a rubric following this template structure (derived from the working Chox rubric):

```
RUBRIC TEMPLATE STRUCTURE:
1. HOW {PRODUCT} WORKS -- 2-3 sentences explaining the product and integration
2. CRITICAL IMPLEMENTATION REQUIREMENT -- The one thing that MUST be true for a
   developer to use this product
3. STRONG FIT SIGNALS -- 4-6 bullet points that raise the score
4. POOR FIT SIGNALS -- 4-6 bullet points that lower the score
5. SCORING RUBRIC (1-5) -- One sentence per score level with concrete criteria
6. OUTPUT FORMAT -- JSON with score and reason
```

The Chox rubric in `score_leads.py` is the gold standard reference. It works because it is specific and opinionated. The rubric generation prompt must produce rubrics of equal specificity for any product.

### Scoring Model Choice

**Use Claude Haiku (claude-haiku-4-5) for scoring.** It is fast, cheap ($0.001/lead at current pricing), and accurate enough for a 1-5 classification task. Sonnet would be overkill. At 500 leads/month per client and 20 clients, that is 10,000 scoring calls/month at roughly $10 total. Negligible.

### Scoring Data Sent to Claude

For each lead, the scoring call includes:
- `repo_name`, `repo_description`, `repo_stars`
- `frameworks_detected`, `risk_apis_detected` (from code search during discovery)
- `profile_bio`, `profile_company`, `profile_location`
- `readme` (up to 3000 chars)

This is the same data structure as the current `score_lead()` function in `score_leads.py`. The `relevant` dict construction does not change.

### Why This Matters

Every other outreach tool sends emails to everyone who matches a surface-level filter (job title, company size, technology tag). Ghostline reads the developer's actual code and README, evaluates whether the client's product is genuinely relevant to what they are building, and only emails developers where the answer is "yes, probably" or better. This is why reply rates will be higher, and why clients will stay.

---

## 7. Discovery Pipeline -- Multi-Client Architecture

### Current Architecture (Single Client)

```
SEARCH_QUERIES (hardcoded in config.py)
    -> discover_repos() fetches repos from GitHub Search API
    -> qualify/score module evaluates repos
    -> email extraction from profiles/commits/events
    -> leads written to Google Sheet
```

### SaaS Architecture (Multi-Client)

```
Per-client pipeline run:
    client_config loaded from Postgres
        -> config.search_queries (AI-generated, stored as JSONB)
        -> discover_repos(client_config) fetches repos via Ghostline PAT pool
        -> blocklist filtering (global + client-specific)
        -> profile enrichment + email extraction
        -> fit scoring with client's scoring_rubric
        -> leads written to Postgres (client_id scoped)
        -> qualified leads (score 3+) queued for outreach
        -> zero-result alert check at each stage
```

### Key Refactoring

The `discover_repos()` function in `discovery/discover.py` currently imports `SEARCH_QUERIES` and `PAGES_PER_QUERY` from `shared/config.py` at module level. In the SaaS version:

- `discover_repos()` accepts a `ClientConfig` parameter
- Search queries come from `config.search_queries`
- `GitHubClient` is instantiated with a token from Ghostline's PAT pool (round-robin or least-recently-used selection)
- Blocklists are merged: `GLOBAL_BLOCKLIST + config.custom_blocklists`

The `GitHubClient` class in `discovery/github_client.py` currently reads `GITHUB_HEADERS` from `shared/config.py` at module level. In the SaaS version:

- `GitHubClient.__init__()` accepts a `github_token` parameter
- Headers are constructed from the passed token, not from a global

### GitHub PAT Pool

Ghostline maintains a pool of 5-10 GitHub Personal Access Tokens (no scopes needed — public data only). Each token gets 5,000 core API calls/hour and 30 search calls/minute. At 20 clients staggered across the day, a pool of 5 tokens is sufficient.

- Pool is managed as an environment variable (`GITHUB_PAT_POOL=token1,token2,...`)
- Token selection: round-robin, skipping any token with <500 remaining core calls
- If all tokens are exhausted: pipeline task fails with a clear error, alert sent to Ghostline ops
- Tokens are rotated quarterly as a security practice

### Platform Expansion Path (Future)

GitHub is the core platform and the only one to build for now. The architecture is designed so additional discovery sources can be added later without rewriting the pipeline:

**Potential future sources** (do not build these now):
- **npm/PyPI download signals** -- If a client's product is an npm package, find repos that `npm install` it
- **Stack Overflow** -- Find developers asking/answering questions about the client's technology. Extract GitHub profiles from SO profiles.
- **Docker Hub** -- Find developers pulling the client's Docker image
- **GitHub Discussions/Issues** -- Find developers asking questions in the client's own repo (for companies with existing OSS presence)

**How to keep the door open**: The `ClientConfig` includes a `discovery_sources` field (default: `["github_search"]`). The pipeline runner dispatches to the appropriate discovery module based on this field. For now only `github_search` is implemented. Adding `npm_downloads` or `stackoverflow` later means writing a new discovery module and adding it to the dispatch.

---

## 8. Outreach Pipeline -- Per-Client Email Personalization

### Current Architecture

`email_generator.py` loads `CHOX_CONTEXT.md` from disk at import time and hardcodes it into `_SYSTEM_PROMPT`. The entire system prompt is Chox-specific: product description, email structure, tone, sign-off, banned words.

### SaaS Architecture

The system prompt is built dynamically at call time from the client's `email_context_doc` field:

```python
def _build_system_prompt(config: ClientConfig) -> str:
    return f"""\
You are a cold email copywriter for {config.product_name}.
You write short, personalized outreach emails to developers.

PRODUCT CONTEXT:
{config.email_context_doc}

EMAIL CONSTRAINTS:
{GLOBAL_EMAIL_CONSTRAINTS}  # shared across all clients

SIGN-OFF:
{config.sender_signoff}

TONE:
{GLOBAL_TONE_GUIDELINES}  # shared across all clients

BANNED WORDS:
{GLOBAL_BANNED_WORDS}  # shared across all clients
"""
```

Some parts of the email prompt are global (banned words, formatting rules, parse format) and some are per-client (product context, sign-off, CTA). This split avoids duplicating quality controls across every client config.

### Email Generation Flow

1. Load qualified leads (score 3+, not yet contacted) for the client
2. For each lead, fetch README via `fetch_readme()` using a token from Ghostline's PAT pool
3. Build per-client system prompt from `config.email_context_doc`
4. Build per-lead user prompt from lead data + README
5. Call Claude Sonnet (creative task, needs the better model)
6. Parse response into subject + body
7. Run content safety filter (check for external links, phishing patterns, impersonation)
8. Clean emails → status `pending` in `email_drafts`. Flagged emails → status `flagged` for manual review.

### Email Review & Auto-Send

Emails are fully automated by default. The client does not need to review anything for the system to work.

**How it works**:
- Generated emails land in the client's dashboard review queue
- **Auto-send after 24 hours** unless the client explicitly rejects an email
- Clients who want to review can log into the dashboard and approve/reject/edit before the 24-hour window closes
- Clients who want fully hands-off just ignore the queue and emails go out on schedule

**Safety guardrails (automated, no human intervention needed)**:
- **Content safety filter** on every generated email — checks for phishing, external links, credential requests, impersonation. Flagged emails are held, not queued.
- **Content safety filter on client edits** — if a client edits an email body in the dashboard, the edited version is re-screened before sending.
- Warm-up pacing enforced automatically (5/day week 1-2, scaling to 20/day by week 7+)
- Auto-pause if weekly bounce rate exceeds 5% (via SES bounce webhook)
- Auto-pause if spam complaint rate exceeds 0.1% (via SES complaint webhook)
- Fit scoring at 3+ threshold ensures only relevant leads get emailed
- Hard daily sending cap per tier enforced at the Celery task level

**Dashboard setting**: Clients can toggle between "auto-send" (default) and "manual review required" modes in settings. Most clients will leave auto-send on.

---

## 9. Technical Architecture

### Overview

Three layers: the pipeline engine (existing Python code, parameterized), a multi-tenant orchestration layer (new), and a self-serve web dashboard (new).

```
[Web Dashboard + Self-Serve Onboarding]     [Admin Dashboard (Ghostline ops)]
        |                                            |
[Orchestration: Client Registry + Job Scheduler (Celery + Redis)]
        |
[Per-Client Pipeline Runner (Celery tasks, NOT LangGraph)]
  client_id -> ClientConfig -> runs pipeline stages
        |
[Pipeline Stages (Celery tasks)]
  discover -> filter -> enrich -> score_fit -> generate_emails -> content_filter -> auto_send
        |
[Shared Infrastructure]
  PostgreSQL (all data, client_id scoped)
  Amazon SES (email sending, bounce/complaint webhooks)
  GitHub PAT pool (5-10 tokens, round-robin)
  Central Anthropic API key
```

**Note on LangGraph**: The current outreach pipeline uses a LangGraph StateGraph with CLI-based human-in-the-loop review (`outreach_graph.py`). The SaaS version replaces this with simple Celery tasks — the auto-send model with dashboard review is fundamentally different from the interrupt-based CLI loop. The LangGraph graph, checkpoint DB, and CLI review code (`review_cli.py`) become dead code in the SaaS version. Individual node functions (email generation, sending) are reused but orchestrated by Celery, not LangGraph.

### ClientConfig Dataclass

```python
@dataclass
class ClientConfig:
    # Identity
    client_id: str
    client_name: str
    product_name: str
    plan: str  # "starter" | "growth" | "scale"

    # Discovery
    search_queries: list[str]           # AI-generated GitHub search queries
    discovery_sources: list[str]        # ["github_search"] for now
    custom_blocklists: dict             # additive overrides to global blocklists
    pages_per_query: int                # default 10
    max_leads_per_run: int              # tier-dependent

    # Fit scoring
    scoring_rubric: str                 # AI-generated system prompt for scoring
    scoring_model: str                  # "claude-haiku-4-5-20251001"
    fit_threshold: int                  # 3 (fixed, not client-configurable)

    # Email generation
    email_context_doc: str              # AI-generated email system prompt
    sender_name: str
    reply_to_email: str                 # where replies land (client's email)
    sender_signoff: str                 # full sign-off block

    # Pacing
    max_emails_per_day: int             # tier-dependent
    warm_up_week: int                   # current warm-up week (affects daily limit)
    batch_size: int                     # default 10

    # Settings
    auto_send_enabled: bool             # default True (auto-send after 24hr)
```

**What's NOT in ClientConfig** (managed at the platform level):
- **GitHub token**: Comes from Ghostline's PAT pool, not per-client
- **SMTP credentials**: Ghostline sends via Amazon SES, not client Gmail
- **Google Sheets**: Dropped. Postgres + CSV export in dashboard
- **Anthropic API key**: Central key, not per-client

### Database Schema (PostgreSQL)

```sql
-- Core multi-tenancy
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'starter',
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, churned
    created_at TIMESTAMPTZ DEFAULT now(),
    onboarded_at TIMESTAMPTZ
);

CREATE TABLE client_configs (
    client_id UUID PRIMARY KEY REFERENCES clients(id),

    -- Discovery
    search_queries JSONB NOT NULL DEFAULT '[]',
    discovery_sources JSONB NOT NULL DEFAULT '["github_search"]',
    custom_blocklists JSONB DEFAULT '{}',
    pages_per_query INT DEFAULT 10,
    max_leads_per_run INT DEFAULT 500,

    -- Fit scoring
    scoring_rubric TEXT NOT NULL,
    scoring_model TEXT DEFAULT 'claude-haiku-4-5-20251001',

    -- Email generation
    email_context_doc TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    reply_to_email TEXT NOT NULL,
    sender_signoff TEXT NOT NULL,

    -- Pacing
    max_emails_per_day INT DEFAULT 10,
    warm_up_started_at TIMESTAMPTZ,
    batch_size INT DEFAULT 10,

    -- Settings
    auto_send_enabled BOOLEAN DEFAULT TRUE,

    -- Product context (raw inputs, kept for re-generation)
    product_description TEXT,
    integration_method TEXT,
    target_developer_profile TEXT,
    good_fit_criteria TEXT,
    bad_fit_criteria TEXT,
    competitors TEXT
);

-- Pipeline execution
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',  -- running, completed, failed
    repos_discovered INT DEFAULT 0,
    leads_added INT DEFAULT 0,
    leads_scored INT DEFAULT 0,
    leads_qualified INT DEFAULT 0,  -- score 3+
    emails_generated INT DEFAULT 0,
    emails_sent INT DEFAULT 0,
    errors JSONB DEFAULT '[]'
);

-- Lead storage
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    github_username TEXT NOT NULL,
    email TEXT,
    full_name TEXT,
    repo_url TEXT,
    repo_name TEXT,
    repo_description TEXT,
    repo_stars INT DEFAULT 0,
    repo_language TEXT,
    frameworks_detected TEXT,
    risk_apis_detected TEXT,
    profile_bio TEXT,
    profile_company TEXT,
    profile_location TEXT,
    profile_blog TEXT,
    twitter_handle TEXT,
    followers INT DEFAULT 0,
    public_repos INT DEFAULT 0,
    email_source TEXT,

    -- Fit scoring
    fit_score INT,                      -- 1-5
    fit_reason TEXT,                     -- one-sentence explanation

    -- Outreach status
    contacted BOOLEAN DEFAULT FALSE,
    contacted_at TIMESTAMPTZ,
    response_status TEXT DEFAULT 'none',

    -- Metadata
    discovered_at TIMESTAMPTZ DEFAULT now(),
    run_id UUID REFERENCES pipeline_runs(id),

    UNIQUE(client_id, github_username, repo_name)
);

CREATE INDEX idx_leads_client_fit ON leads(client_id, fit_score) WHERE fit_score >= 3;
CREATE INDEX idx_leads_client_uncontacted ON leads(client_id) WHERE contacted = FALSE AND fit_score >= 3;

-- Email tracking
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected, sent, bounced, failed
    edited_body TEXT,
    sent_at TIMESTAMPTZ,
    send_error TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Lead scoring feedback (thumbs up/down from client — feeds future rubric refinement)
CREATE TABLE lead_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    feedback TEXT NOT NULL,  -- 'thumbs_up' or 'thumbs_down'
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, lead_id)
);

-- Client notifications (zero-result alerts, usage warnings, etc.)
CREATE TABLE client_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    notification_type TEXT NOT NULL,  -- 'zero_result', 'bounce_pause', 'usage_warning', 'infra_error'
    message TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now(),
    acknowledged BOOLEAN DEFAULT FALSE
);

-- AI generation audit trail
CREATE TABLE ai_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    generation_type TEXT NOT NULL,  -- 'queries', 'rubric', 'email_prompt', 'fit_score', 'email'
    input_summary TEXT,
    output TEXT,
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Credentials & Secrets

Platform-level secrets (stored in environment variables on the VPS, never in the database):
- `GHOSTLINE_PAT_POOL` — comma-separated GitHub PATs for the token pool
- `ANTHROPIC_API_KEY` — central API key for all Claude calls
- `AWS_SES_ACCESS_KEY_ID` + `AWS_SES_SECRET_ACCESS_KEY` — Amazon SES sending credentials
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` — Stripe API and webhook verification
- `CLERK_SECRET_KEY` — Clerk auth backend key

No per-client secrets are stored in the database. GitHub tokens come from the platform pool. Email sending uses platform SES. The only client-specific credential is their Stripe subscription ID, which is not sensitive.

### Scheduling and Automation

**Recommended**: Celery + Redis on a single VPS.

Celery Beat triggers these tasks:
- `run_pipeline_for_client(client_id)` — daily per client, staggered by 30 minutes. Loads `ClientConfig` from Postgres, selects a GitHub PAT from the pool, runs discovery → scoring → email generation → content filter → insert pending emails.
- `auto_send_pending_emails()` — runs hourly. For each `email_draft` where `status = 'pending'` and `created_at < now() - 24 hours` and `client.auto_send_enabled = TRUE`: re-check status at send time (race condition guard), send via SES, update status.
- `process_ses_feedback()` — webhook handler (not a Celery Beat task, but a FastAPI endpoint). Processes SES bounce/complaint notifications via SNS. Updates `email_drafts` status and checks auto-pause thresholds.
- `send_weekly_digest(client_id)` — weekly per client (Monday 9am in client's timezone, defaulting to UTC). Generates digest with stats + "lead of the week."
- `check_alert_thresholds(client_id)` — runs after each pipeline run. Checks for zero-result stages, sends client notifications.

Redis is the broker (Upstash free tier for MVP, local Redis at scale). Redis also serves as the backend for SSE progress updates during onboarding dry runs.

**Warm-up schedule** (automatic, based on `warm_up_started_at`):

| Week | Emails/day |
|---|---|
| 1-2 | 5 |
| 3-4 | 10 |
| 5-6 | 15 |
| 7+ | 20 (or plan maximum) |

The pipeline checks `warm_up_started_at` at runtime and applies the correct daily limit. No manual intervention.

**Stagger example (10 clients):**
```
Client 1: 06:00 UTC daily
Client 2: 06:30 UTC daily
Client 3: 07:00 UTC daily
...
Client 10: 10:30 UTC daily
```

### Web Dashboard -- Recommended Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui | Professional dashboard in hours, zero-config Vercel deploy |
| Backend API | FastAPI (Python) | Same language as pipeline, async-first, automatic OpenAPI docs |
| Database | PostgreSQL (Supabase or Railway managed) | Reliable, built-in row-level security potential |
| Auth | Clerk (magic link or Google OAuth) | Zero password management, works in minutes |
| Hosting (frontend) | Vercel (free tier) | Zero-config, global CDN |
| Hosting (backend + pipeline) | Single VPS (Hetzner CX21, 2 vCPU, 4GB RAM) | $6/month, runs FastAPI + Celery + Redis |
| Job queue | Celery + Redis (Upstash free tier) | Native Python, reliable scheduling |

**Client dashboard pages (Phase 1 — these ARE the product):**
1. **Leads table** -- cursor-paginated, filterable by fit score / contacted / date, sortable. Shows fit_score and fit_reason inline. **Thumbs-up/down buttons** on each lead for scoring feedback (stored in `lead_feedback` table, enables future rubric auto-refinement).
2. **Pipeline runs** -- per-run history with stats (repos found, leads scored, qualified, emails sent).
3. **Email review queue** -- pending drafts with approve/reject/edit. Shows 24-hour auto-send countdown. Content safety filter results visible on flagged emails.
4. **Emails sent** -- subject, recipient, sent_at, status (sent/bounced/failed).
5. **Campaign config** -- editable view of search queries, scoring rubric, email prompt. "Re-generate" button for each. Query editor with live result count preview.
6. **Settings** -- plan, usage vs. limits, warm-up progress, auto-send toggle, reply-to email, CSV export button.

**Admin dashboard (Phase 1 — Ghostline ops, protected by Clerk role):**
1. **Client list** -- all clients with status indicators (active/paused/churned), last pipeline run status, MRR.
2. **Pipeline health** -- global view of all pipeline runs, error rates, failed runs.
3. **PAT pool status** -- remaining rate limit per token, rotation schedule.
4. **SES reputation** -- bounce rate, complaint rate, sending volume across all clients.
5. **Alert log** -- all client notifications sent, acknowledgment status.

### Data Isolation

1. **Database**: Every table has `client_id` FK. All queries scoped `WHERE client_id = ?`. No cross-client queries ever. FastAPI dependency injection extracts `client_id` from the Clerk auth token and passes it to every query — no raw UUID manipulation in URLs.
2. **Email sending**: All emails sent from Ghostline's SES domain (`send.ghostline.ai`). Per-client `reply_to_email` ensures replies go to the client. SES bounce/complaint metrics tracked per client via `client_id` tag on each sent email.
3. **API keys**: Central Anthropic API key for all Claude calls. Central GitHub PAT pool shared across clients. No per-client API keys needed.
4. **Admin access**: Admin dashboard protected by Clerk role-based access. Only Ghostline team members can see cross-client data.

---

## 10. Business Model & Pricing

### Pricing Tiers

**Starter -- $299/month**
- 1 campaign (single ICP / query set)
- Up to 200 leads discovered/month
- Up to 60 emails sent/month (warm-up paced)
- AI-generated queries, rubric, and email prompt
- Fit scoring on all leads (score 3+ get outreach)
- Dashboard: leads table, email queue, pipeline stats
- CSV export
- Email support

**Growth -- $599/month**
- Up to 3 campaigns (3 distinct ICPs or frameworks)
- Up to 600 leads discovered/month
- Up to 150 emails sent/month
- Everything in Starter plus:
- Multi-campaign management (different ICPs, different query sets)
- Weekly email digest with pipeline stats
- Priority email support

**Scale -- $1,199/month**
- Unlimited campaigns
- Up to 1,500 leads/month
- Up to 300 emails/month
- Everything in Growth plus:
- Quarterly auto-refresh of queries and rubric (system re-generates based on latest GitHub trends)
- API access: programmatic lead export, webhooks on new qualified leads
- Priority support (24-hour response SLA)

**Annual discount**: 20% off for annual prepay. Improves cash flow, reduces churn.

### Cost Structure Per Client

| Item | Cost/month |
|---|---|
| Fit scoring (Claude Haiku, ~500 leads) | ~$0.50 |
| Email generation (Claude Sonnet, ~60 emails) | ~$1.80 |
| Query generation (one-time, amortized) | ~$0.01 |
| Rubric generation (one-time, amortized) | ~$0.01 |
| **Total AI cost per Starter client** | **~$2.30** |
| **Total AI cost per Growth client** | **~$6.50** |
| **Total AI cost per Scale client** | **~$15.00** |

**Gross margin per client**: 97-99%. The AI costs are negligible relative to pricing.

### Path to $10k MRR

| Scenario | Clients | Mix | MRR |
|---|---|---|---|
| All Growth | 17 | 17 x $599 | $10,183 |
| Mixed | 16 | 8 x $299 + 5 x $599 + 3 x $1,199 | $10,184 |
| Scale-anchored | 9 | 1 x $599 + 8 x $1,199 | $10,191 |

**Practical target**: 10 Growth + 3 Scale clients to cross $10k. Achievable in 6-9 months from first paying client.

### Estimated Monthly Infrastructure Cost

| Item | Cost |
|---|---|
| VPS (Hetzner CX21: 2 vCPU, 4GB RAM) | $6/month |
| Managed Postgres (Supabase free tier) | $0-10/month |
| Redis (Upstash free tier) | $0-5/month |
| Anthropic API (10 clients) | ~$50/month |
| Amazon SES (10 clients, ~600 emails/month) | ~$0.60/month |
| Vercel (frontend) | $0 |
| Domain + email | $10/month |
| **Total at 10 clients** | **~$75-85/month** |

**Gross margin at $6k MRR: ~99%.** SES costs are negligible ($0.10 per 1,000 emails). The dominant cost is Anthropic API usage.

---

## 11. GTM Strategy

### Positioning

**Tagline**: "Find developers who can actually use your product."

**Positioning statement**: Ghostline is the only outreach platform that reads a developer's code before deciding whether to email them. For B2B companies selling to developers, Ghostline finds leads on GitHub by what they're building, scores each one for genuine product fit, and sends personalized emails referencing their actual project. Only qualified leads get outreach. No spray and pray.

### Growth Strategy

The product is fully self-serve. Growth comes from getting dev-tool founders to the signup page and letting the product sell itself. No sales calls, no demos, no "let's hop on a quick call."

**Channel 1: Use Ghostline on itself.** Configure Ghostline to find dev-tool founders on GitHub who are building products that need outreach to developers. Send them personalized emails referencing their actual product repo. The pitch becomes the demo. This is the most credible GTM motion possible and it costs nothing beyond the existing infrastructure.

**Channel 2: Hacker News Show HN.** Post a detailed "how I built this" once the self-serve product is live. The GitHub-native outreach angle + AI fit scoring is genuinely interesting to the HN audience. Focus on the fit scoring differentiator -- "we read their code before emailing them" is a hook. HN drives sign-ups directly to the self-serve flow.

**Channel 3: Product Hunt.** Launch with the working dashboard and self-serve onboarding. Product Hunt audience skews toward founders and indie hackers -- the exact ICP.

**Channel 4: Content / SEO.** One blog post per month:
- "How to find developers using your SDK on GitHub"
- "Why cold email to developers fails (and what works instead)"
- "We scored 2,000 GitHub leads for fit -- here's what we learned"
- "The developer outreach playbook: GitHub-native lead gen explained"

These compound over time. The fit scoring angle is unique content that nobody else can write.

**Channel 5: Indie Hackers.** Post monthly progress updates with real numbers (MRR, leads found, reply rates). The IH audience includes devtool founders who are the exact ICP.

### Launch Pricing

**Founding customer pricing** for first 20 signups: 50% off for the first 3 months (auto-applied via Stripe coupon). Creates early traction and testimonials. No commitment required -- the product should retain on its own merits. Move to full pricing after the coupon period.

### Success Metrics

| Metric | Target |
|---|---|
| Leads discovered/month per client | 200+ (Starter), 400+ (Growth) |
| Fit score 3+ rate | 20-40% of discovered leads |
| Email send rate (sent / qualified leads) | 80%+ |
| Reply rate (replies / sent) | 3-8% (cold developer outreach benchmark) |
| Client MRR by month | Growing |
| Monthly churn | <5% |

---

## 12. Phased Roadmap

### Phase 1 -- Self-Serve MVP to First Paying Client (Weeks 1-8)

**Goal**: Fully self-serve product live, first paying client signs up and runs pipeline without any Ghostline team involvement.

| Week | Work |
|---|---|
| 1-2 | Deploy codebase to VPS. Set up Postgres with schema from Section 9. Implement `ClientConfig` dataclass. Set up Stripe with pricing tiers and checkout flow. Set up Amazon SES with `send.ghostline.ai` domain (SPF/DKIM/DMARC). Set up GitHub PAT pool (5 tokens). |
| 2-3 | **AI generation layer**: Build query generation metaprompt + function. Build rubric generation metaprompt + function. Build email prompt generation function. Build content safety filter. **Write unit tests** for all parsing/validation with golden fixtures using Chox as reference baseline. Test all three generators against Chox (output should match current hardcoded config). |
| 3-4 | **Pipeline as Celery tasks** (NOT LangGraph): Write new Celery tasks that compose existing module functions: `discover_task` (calls `discover_repos()` with config), `score_task` (calls `score_lead()` with per-client rubric), `generate_emails_task` (calls `generate_email()` with per-client prompt + content filter), `auto_send_task` (sends via SES, checks status at send time). `GitHubClient.__init__()` accepts token parameter. Zero-result alert check after each stage. |
| 4-5 | **Dashboard + self-serve onboarding**: Next.js + FastAPI + Clerk auth. Onboarding wizard: product context form (7 fields, localStorage draft save) → AI generation preview (with regenerate button) → dry run with SSE progress → go live. Dashboard pages: leads table (with thumbs-up/down feedback), email review queue (with 24hr countdown + content filter results), pipeline stats, settings (auto-send toggle, reply-to, CSV export). **Admin dashboard**: client list, pipeline health, PAT pool status, SES reputation. |
| 5-6 | **Scheduling + alerts**: Celery Beat for daily pipeline runs (staggered), hourly auto-send, weekly digest (with "lead of the week"). Zero-result alerts. Bounce/complaint auto-pause via SES SNS webhook. Usage warning emails at 80% of plan limits. |
| 6-7 | **Onboard Chox as Client 0**: Run the full self-serve flow for Chox. Verify AI-generated queries, rubric, and email prompt produce equivalent results to current hardcoded versions. Fix any issues in the onboarding flow. |
| 7-8 | **Marketing site + launch**: Build landing page with pricing and **"Preview your pipeline" CTA** (paste product description, see 3 sample leads — no account required). Set up founding customer coupon in Stripe. Use Ghostline on itself to find first clients (dev-tool founders on GitHub). Go live. |

### Phase 2 -- Scale to $10k MRR (Months 3-6)

**Goal**: 15-20 paying clients, all self-serve, no manual intervention.

| Month | Work |
|---|---|
| 3 | **GTM push**: Show HN post. Product Hunt launch. Ghostline outreach to dev-tool companies. 1 blog post/month. |
| 3-4 | **Follow-up sequences**: 2-touch sequence (initial + 1 follow-up after 5 days if no reply). A/B email prompt testing (2 variants, system alternates and reports open/reply rates). |
| 4-5 | **Operational hardening**: Automated bounce rate monitoring with auto-pause. Automated weekly digest emails per client. Error alerting (pipeline failures, SMTP issues). Pipeline retry logic. |
| 5-6 | **Multi-campaign UI**: Allow Growth/Scale clients to create multiple campaigns from the dashboard (different ICPs, different query sets, different rubrics). |

### Phase 3 -- Growth (Month 6+)

**Goal**: $25k+ MRR, product-led growth, zero manual work.

- Reply tracking and response analytics in dashboard
- CRM integrations (HubSpot, Pipedrive): push qualified leads directly
- API access for Scale clients: programmatic lead export, webhooks on new qualified leads
- Public marketing site with case studies and concrete metrics (reply rates, demos booked)
- Quarterly auto-refresh: system re-generates queries and rubric using latest GitHub trends (Scale tier)
- **Platform expansion**: npm/PyPI signal integration as a second discovery source
- White-label offering for developer marketing agencies
- Referral program: clients get 1 month free for each referral that converts

---

## 13. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **GitHub API policy changes** | High | Use Ghostline-owned PAT pool (5-10 tokens, public data only, no scopes). Stay within rate limits with built-in budget monitoring. If any token is exhausted, pipeline fails cleanly with alert to ops. Monitor GitHub changelog. Graceful degradation already built in. If GitHub restricts search API, the code search and repo content APIs are harder to restrict since they serve core GitHub functionality. |
| **Email deliverability / spam** | High | Ghostline owns the sending domain (`send.ghostline.ai`) with proper SPF/DKIM/DMARC. Enforce warm-up schedule automatically. Content safety filter on every generated email. Auto-pause client if bounce rate >5% or spam complaint rate >0.1% (via SES feedback loop). Fit scoring at 3+ threshold is the primary mitigation — higher relevance means lower spam reports. |
| **Sending domain reputation burned by bad client** | Medium | Content safety filter catches most abuse. Hard daily sending caps per tier. Auto-pause on bounce/complaint thresholds. If a client sends abusive content via edited emails, the content filter re-screens edits before sending. Worst case: one client's volume is small enough that a single bad actor cannot burn the entire domain. Future mitigation: per-client subdomain isolation (deferred). |
| **AI-generated rubrics produce poor scoring** | Medium | The dry-run step during onboarding shows the client 5 scored leads before they go live -- they can see if the rubric makes sense. Allow rubric editing in the dashboard. Monitor qualified-lead rate per client automatically (if <10% or >80% of leads score 3+, send the client an alert suggesting they refine their fit criteria). Keep the Chox rubric as a gold-standard reference for AI generation. |
| **AI-generated queries return irrelevant repos** | Medium | The AI generation preview during onboarding shows the client sample repos from each query before they go live. Allow query editing in the dashboard. Quarterly auto-refresh for Scale tier clients. Clients can manually trigger a query re-generation from the dashboard at any time. |
| **Two-person team bandwidth at scale** | Low | Product is fully self-serve -- no onboarding calls, no manual email review, no manual client setup. Automate monitoring aggressively (pipeline digest emails, error alerts on exception). Team time goes to product improvement and GTM, not client servicing. |
| **Client churn from poor lead quality** | Medium | Dry-run during onboarding shows real results before the client commits. Dashboard shows expected benchmarks inline (3-8% reply rates are normal for cold developer outreach). Offer month-1 satisfaction credit if pipeline underdelivers (<50 leads scored 3+ or <30 emails sent). Fit scoring is the structural defense -- if leads are truly relevant, clients stay. |
| **Anthropic API dependency** | Low | `email_generator.py` and `score_leads.py` both isolate the LLM call behind a clean function boundary. Switching to OpenAI or another provider is a 1-hour change per module. Keep the option open but do not over-abstract now. |
| **Competition from Reo.dev / Common Room** | Low | They serve enterprise ($15k+/year contracts). Ghostline serves SMB ($299-1,199/month). They provide signal intelligence. Ghostline provides end-to-end outreach. Different products for different markets. If they move downmarket, the fit scoring system and GitHub-native personalization are hard to replicate because they require per-client AI configuration that scales with human judgment, not just data aggregation. |
| **GitHub rate limiting across many clients** | Low | Ghostline PAT pool (5-10 tokens). Each token gets 5,000 core calls/hour and 30 search calls/minute. At 20 clients with staggered schedules and round-robin token selection, no single token is over-stressed. Pool is monitored via admin dashboard; tokens with <500 remaining calls are skipped. |

---

## 14. Immediate Next Steps (This Week)

In priority order:

1. **Deploy to VPS + set up infrastructure** -- Hetzner VPS, Postgres (schema from Section 9), Redis, Amazon SES (`send.ghostline.ai` with SPF/DKIM/DMARC), GitHub PAT pool (5 tokens), Stripe products + webhook endpoint, Clerk application.
2. **Build AI generation layer + content filter** -- query generation, rubric generation, email prompt generation, content safety filter. Write unit tests with golden fixtures using Chox as baseline. This is the highest-leverage new code.
3. **Create `ClientConfig` dataclass** -- loads from Postgres, no per-client secrets (platform PAT pool + SES + central Anthropic key).
4. **Build pipeline as Celery tasks** -- `discover_task`, `score_task`, `generate_emails_task`, `auto_send_task`. Compose existing module functions (`discover_repos()`, `score_lead()`, `generate_email()`) with `ClientConfig` parameters. Replace LangGraph outreach graph entirely. Add zero-result alert checks.
5. **Build self-serve onboarding + dashboard** -- Stripe Checkout → Clerk auth → 7-field product context form → AI generation preview (with regenerate) → dry run with SSE progress → go live. Dashboard: leads table (with thumbs-up/down), email queue (with auto-send countdown), pipeline stats, settings. Admin dashboard: client health, PAT pool, SES reputation.
6. **Set up Celery Beat scheduling** -- daily pipeline runs (staggered), hourly auto-send, weekly digest (with lead of the week), post-run alert checks, SES bounce/complaint webhook processing.
7. **Onboard Chox as Client 0** -- full self-serve flow end-to-end. Verify AI-generated config matches hardcoded originals.
8. **Marketing site + launch** -- landing page with "Preview your pipeline" CTA (paste product description, see 3 sample leads, no account required). Pricing page. Stripe founding customer coupon. Use Ghostline on itself to find dev-tool founders. Go live.

The dashboard, self-serve onboarding, and admin dashboard are not "Phase 2" -- they ARE the product. Ship them before accepting any clients.

---

### Key Files to Refactor

| File | Change |
|---|---|
| `shared/config.py` | Extract all hardcoded globals into `ClientConfig` dataclass that loads from Postgres |
| `score_leads.py` | `SYSTEM_PROMPT` becomes per-client `scoring_rubric` loaded from `client_configs`; `score_lead()` function reused by Celery score task |
| `outreach/email_generator.py` | Replace hardcoded `CHOX_CONTEXT.md` load with dynamic prompt construction from `config.email_context_doc`; `generate_email()` function reused by Celery email task |
| `outreach/email_sender.py` | Replace Gmail SMTP with Amazon SES API calls; reuse send logic |
| `discovery/github_client.py` | `__init__` accepts `github_token` parameter instead of reading from global config |
| `discovery/discover.py` | `discover_repos()` accepts `ClientConfig`, iterates over `config.search_queries` |

### Dead Code (Replace, Do Not Refactor)

| File | Fate |
|---|---|
| `outreach/outreach_graph.py` | **Replace with Celery tasks.** LangGraph StateGraph with CLI interrupt does not translate to web auto-send. Individual node functions (generate, send) are reused but orchestrated by Celery. |
| `outreach/outreach_state.py` | **Replace.** `OutreachState` TypedDict replaced by Postgres `email_drafts` table + Celery task state. |
| `outreach/review_cli.py` | **Replace.** CLI review replaced by dashboard email queue with auto-send. |
| `shared/sheets.py` | **Drop.** Google Sheets integration removed. Postgres + CSV export in dashboard. |
| `outreach/outreach_sheets.py` | **Drop.** Sheet read/write replaced by Postgres queries. |
| `ghostline_outreach.db` | **Drop.** SQLite checkpoint DB replaced by Postgres. |

### New Files to Create

| File | Purpose |
|---|---|
| `saas/client_config.py` | `ClientConfig` dataclass + loader from Postgres |
| `saas/tasks.py` | Celery tasks: `run_pipeline_for_client`, `auto_send_pending_emails`, `send_weekly_digest`, `check_alert_thresholds` |
| `saas/ai_generation.py` | Query generation, rubric generation, email prompt generation functions |
| `saas/content_filter.py` | Post-generation content safety screening |
| `saas/ses_sender.py` | Amazon SES email sending + bounce/complaint webhook handler |
| `saas/pat_pool.py` | GitHub PAT pool management (selection, rotation, health monitoring) |
| `tests/test_ai_generation.py` | Unit tests for AI generation parsing/validation |
| `tests/test_content_filter.py` | Unit tests for content safety screening |
| `tests/test_auto_send.py` | Unit tests for auto-send eligibility and status checking |
| `tests/fixtures/` | Golden fixture files (saved Claude responses for Chox) |

---

*Generated: 2026-03-23. Revised: 2026-03-23 (architecture review: PAT pool, SES sending, Celery tasks, admin dashboard, content safety, SSE dry run, lead feedback, zero-result alerts, landing preview).*
