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
7. **Sender identity** -- Name, email, company, sign-off line, CTA preference (e.g., "reply to this email" vs. "try our free tier").
8. **SMTP credentials** -- Gmail + app password (or Google Workspace).

That is 8 fields. No unnecessary information. Every field feeds directly into query generation, rubric generation, or email generation. Nothing is collected that the system does not use.

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
4. Email appears in the client's dashboard review queue. Clients can approve, reject, or edit individual emails. **Default behavior: emails auto-send after 24 hours unless the client rejects them.** This means clients who want a hands-off experience get exactly that, while cautious clients can still review before anything goes out.
5. Approved/auto-approved emails are sent via the client's SMTP, paced according to warm-up schedule

### Step 8: Results Written Back

- Lead status updated in Postgres
- Google Sheet updated (if client uses sheet integration)
- Pipeline run stats recorded (repos found, leads scored, emails sent)

---

## 4. Onboarding Flow (Fully Self-Serve)

The entire onboarding is automated. No calls, no manual setup, no Ghostline team involvement. The client signs up and the system handles everything.

### Self-Serve Onboarding Steps

1. **Stripe Checkout** -- Client selects a plan and enters payment info. Stripe creates the subscription.
2. **Magic link auth** -- Client receives a login link via email (Clerk). Lands in the dashboard.
3. **Product context form** -- The 8 fields from Section 3, Step 1. Clean, guided form with placeholder examples for each field. Tooltips explain what each field is used for. This is the only manual input the client ever provides.
4. **AI generation preview** -- System immediately generates:
   - Search queries (10-20)
   - Fit scoring rubric
   - Sample email system prompt

   All three are shown in a preview screen. The client can review and optionally edit any of them, or accept the defaults. Most clients will accept defaults -- the AI generation is good enough.
5. **Dry run** -- System discovers 10 repos using the generated queries, scores 5 leads, generates 2 sample emails. Client sees real results from their own config before anything goes live. This builds confidence and lets them catch any obvious issues.
6. **Credential input** -- Gmail SMTP + app password with a guided setup walkthrough (inline instructions with screenshots for enabling 2FA and generating app passwords). Live validation: system sends a test email to the client's own address to confirm SMTP works.
7. **Go live** -- Client clicks "Start Pipeline". First discovery run begins within 1 hour. Warm-up schedule starts automatically.

**Total time from signup to live pipeline: ~15 minutes.**

No onboarding calls. No manual client config by Ghostline. No waiting for approval from the Ghostline team. The client is in control from start to finish.

### Automated Retention

- **Weekly digest email**: Automated email showing last week's pipeline stats -- leads discovered, leads scored 3+, emails sent, reply rate (once tracking is in place). Sent every Monday morning.
- **Smart alerts**: Email notification if pipeline encounters errors (SMTP failure, GitHub rate limit exhaustion, 0 leads found for 3 consecutive runs). Client can fix credential issues directly in the dashboard.
- **Usage warnings**: Email when approaching plan limits (80% of leads/month, 80% of emails/month) with upgrade CTA.

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

Queries returning 0 results are dropped. Queries returning 10,000+ results are narrowed. This happens during onboarding (live on the call for Phase 1, automated preview for Phase 2).

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
        -> discover_repos(client_config) fetches repos
        -> blocklist filtering (global + client-specific)
        -> profile enrichment + email extraction
        -> fit scoring with client's scoring_rubric
        -> leads written to Postgres (client_id scoped)
        -> leads synced to client's Google Sheet (optional)
        -> qualified leads (score 3+) queued for outreach
```

### Key Refactoring

The `discover_repos()` function in `discovery/discover.py` currently imports `SEARCH_QUERIES` and `PAGES_PER_QUERY` from `shared/config.py` at module level. In the SaaS version:

- `discover_repos()` accepts a `ClientConfig` parameter
- Search queries come from `config.search_queries`
- `GitHubClient` is instantiated with the client's own GitHub token
- Blocklists are merged: `GLOBAL_BLOCKLIST + config.custom_blocklists`

The `GitHubClient` class in `discovery/github_client.py` currently reads `GITHUB_HEADERS` from `shared/config.py` at module level. In the SaaS version:

- `GitHubClient.__init__()` accepts a `github_token` parameter
- Headers are constructed from the passed token, not from a global

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
2. For each lead, fetch README via `fetch_readme()` using the client's GitHub token
3. Build per-client system prompt from `config.email_context_doc`
4. Build per-lead user prompt from lead data + README
5. Call Claude Sonnet (creative task, needs the better model)
6. Parse response into subject + body
7. Queue for review

### Email Review & Auto-Send

Emails are fully automated by default. The client does not need to review anything for the system to work.

**How it works**:
- Generated emails land in the client's dashboard review queue
- **Auto-send after 24 hours** unless the client explicitly rejects an email
- Clients who want to review can log into the dashboard and approve/reject/edit before the 24-hour window closes
- Clients who want fully hands-off just ignore the queue and emails go out on schedule

**Safety guardrails (automated, no human intervention needed)**:
- Warm-up pacing enforced automatically (5/day week 1-2, scaling to 20/day by week 7+)
- Auto-pause if weekly bounce rate exceeds 5%
- Auto-pause if SMTP credentials stop working (with email alert to client)
- Fit scoring at 3+ threshold ensures only relevant leads get emailed

**Dashboard setting**: Clients can toggle between "auto-send" (default) and "manual review required" modes in settings. Most clients will leave auto-send on.

---

## 9. Technical Architecture

### Overview

Three layers: the pipeline engine (existing Python code, parameterized), a multi-tenant orchestration layer (new), and a self-serve web dashboard (new).

```
[Web Dashboard + Self-Serve Onboarding]
        |
[Orchestration: Client Registry + Job Scheduler]
        |
[Per-Client Pipeline Runner]
  client_id -> ClientConfig -> runs pipeline stages
        |
[Pipeline Stages]
  discover -> filter -> enrich -> score_fit -> generate_emails -> review -> send
        |
[Per-Client Isolated Storage]
  PostgreSQL (all data, client_id scoped) + Client's Google Sheet (optional sync)
```

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
    sender_email: str
    sender_signoff: str                 # full sign-off block

    # Credentials (decrypted at runtime)
    github_token: str
    smtp_username: str
    smtp_password: str

    # Pacing
    max_emails_per_day: int             # tier-dependent
    warm_up_week: int                   # current warm-up week (affects daily limit)
    batch_size: int                     # default 10

    # Storage
    spreadsheet_id: str                 # Google Sheet ID (optional)
    service_account_json: str           # encrypted service account JSON
```

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
    sender_email TEXT NOT NULL,
    sender_signoff TEXT NOT NULL,

    -- Credentials (Fernet encrypted)
    github_token_enc BYTEA NOT NULL,
    smtp_username TEXT NOT NULL,
    smtp_password_enc BYTEA NOT NULL,
    anthropic_api_key_enc BYTEA,  -- NULL = use central key
    spreadsheet_id TEXT,
    service_account_json_enc BYTEA,

    -- Pacing
    max_emails_per_day INT DEFAULT 10,
    warm_up_started_at TIMESTAMPTZ,
    batch_size INT DEFAULT 10,

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

### Encryption

All sensitive fields (tokens, passwords, service account JSON) use Fernet symmetric encryption from the `cryptography` library. The encryption key lives in the application's environment variable (`GHOSTLINE_ENCRYPTION_KEY`), never in the database. Decryption happens at pipeline runtime when `ClientConfig` is loaded.

### Scheduling and Automation

**Recommended**: Celery + Redis on a single VPS.

- Celery Beat triggers `run_pipeline_for_client(client_id)` for each active client daily, staggered by 30 minutes
- Each task loads `ClientConfig` from Postgres, decrypts credentials, instantiates a fresh `GitHubClient`, runs the full pipeline
- Redis is the broker (Upstash free tier for MVP, local Redis at scale)

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

**Dashboard pages (Phase 2):**
1. **Leads table** -- paginated, filterable by fit score / contacted / date, sortable. Shows fit_score and fit_reason inline.
2. **Pipeline runs** -- per-run history with stats (repos found, leads scored, qualified, emails sent).
3. **Email review queue** -- pending drafts with approve/reject/edit. Replaces terminal CLI.
4. **Emails sent** -- subject, recipient, sent_at, status (sent/bounced/failed).
5. **Campaign config** -- read-only view of search queries, scoring rubric, email prompt. "Re-generate" button for each.
6. **Settings** -- SMTP status, plan, usage vs. limits, warm-up progress.

### Data Isolation

1. **Database**: Every table has `client_id` FK. All queries scoped `WHERE client_id = ?`. No cross-client queries ever.
2. **Google Sheets**: Each client has their own `spreadsheet_id`. Sheet sync is optional and additive (Postgres is the source of truth).
3. **Email sending**: Each client's SMTP credentials stored encrypted, used exclusively for their outreach.
4. **API keys**: Central Anthropic API key for MVP. Per-client keys as an option for Scale tier.

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
- Google Sheet sync
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
| Vercel (frontend) | $0 |
| Domain + email | $10/month |
| **Total at 10 clients** | **~$70-80/month** |

**Gross margin at $6k MRR: ~99%.**

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
| 1-2 | Deploy codebase to VPS. Set up Postgres with schema from Section 9. Implement `ClientConfig` dataclass with Fernet encryption. Set up Stripe with pricing tiers and checkout flow. |
| 2-3 | **AI generation layer**: Build query generation metaprompt + function. Build rubric generation metaprompt + function. Build email prompt generation function. Test all three with Chox as the reference client (output should match current hardcoded config). |
| 3-4 | **Pipeline parameterization**: Refactor `discover.py` to accept `ClientConfig`. Refactor `GitHubClient` to accept token parameter. Refactor `email_generator.py` to build system prompt dynamically. Refactor `score_leads.py` to use per-client rubric. Add `client_config` to `OutreachState`. |
| 4-5 | **Dashboard + self-serve onboarding**: Next.js + FastAPI + Clerk auth. Build the full onboarding wizard: product context form → AI generation preview → dry run → credential input with live validation → go live. Build core dashboard pages: leads table, email review queue, pipeline stats, settings. |
| 5-6 | **Scheduling + auto-send**: Implement Celery + Redis scheduler. Create `run_pipeline_for_client(client_id)` task with all stages: discover, score, generate emails, auto-send after 24 hours. Implement warm-up pacing. Implement auto-pause on high bounce rate. |
| 6-7 | **Onboard Chox as Client 0**: Run the full self-serve flow for Chox. Verify that AI-generated queries, rubric, and email prompt produce equivalent results to the current hardcoded versions. Fix any issues in the onboarding flow. |
| 7-8 | **Marketing site + launch**: Build landing page with pricing. Set up founding customer coupon in Stripe. Use Ghostline on itself to find first clients (dev-tool founders on GitHub). Go live. |

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
| **GitHub API policy changes** | High | Use authenticated tokens only, stay within rate limits, each client provides their own PAT (public data only, no scopes). Monitor GitHub changelog. Graceful degradation already built in. If GitHub restricts search API, the code search and repo content APIs are harder to restrict since they serve core GitHub functionality. |
| **Gmail deliverability / spam** | High | Enforce warm-up schedule automatically. Monitor bounce rates per client with auto-pause at 5% weekly bounce rate. Recommend Google Workspace for serious senders. Fit scoring is the primary mitigation -- higher relevance means lower spam reports. |
| **AI-generated rubrics produce poor scoring** | Medium | The dry-run step during onboarding shows the client 5 scored leads before they go live -- they can see if the rubric makes sense. Allow rubric editing in the dashboard. Monitor qualified-lead rate per client automatically (if <10% or >80% of leads score 3+, send the client an alert suggesting they refine their fit criteria). Keep the Chox rubric as a gold-standard reference for AI generation. |
| **AI-generated queries return irrelevant repos** | Medium | The AI generation preview during onboarding shows the client sample repos from each query before they go live. Allow query editing in the dashboard. Quarterly auto-refresh for Scale tier clients. Clients can manually trigger a query re-generation from the dashboard at any time. |
| **Two-person team bandwidth at scale** | Low | Product is fully self-serve -- no onboarding calls, no manual email review, no manual client setup. Automate monitoring aggressively (pipeline digest emails, error alerts on exception). Team time goes to product improvement and GTM, not client servicing. |
| **Client churn from poor lead quality** | Medium | Dry-run during onboarding shows real results before the client commits. Dashboard shows expected benchmarks inline (3-8% reply rates are normal for cold developer outreach). Offer month-1 satisfaction credit if pipeline underdelivers (<50 leads scored 3+ or <30 emails sent). Fit scoring is the structural defense -- if leads are truly relevant, clients stay. |
| **Anthropic API dependency** | Low | `email_generator.py` and `score_leads.py` both isolate the LLM call behind a clean function boundary. Switching to OpenAI or another provider is a 1-hour change per module. Keep the option open but do not over-abstract now. |
| **Competition from Reo.dev / Common Room** | Low | They serve enterprise ($15k+/year contracts). Ghostline serves SMB ($299-1,199/month). They provide signal intelligence. Ghostline provides end-to-end outreach. Different products for different markets. If they move downmarket, the fit scoring system and GitHub-native personalization are hard to replicate because they require per-client AI configuration that scales with human judgment, not just data aggregation. |
| **GitHub rate limiting across many clients** | Low | Each client provides their own PAT. Each PAT gets its own 5,000 core calls/hour and 30 search calls/minute. At 20 clients with staggered schedules, there is no shared bottleneck. Maintain 3-5 Ghostline-owned fallback tokens for clients who do not provide their own. |

---

## 14. Immediate Next Steps (This Week)

In priority order:

1. **Deploy existing codebase to VPS** -- get infrastructure running on Hetzner. Set up Postgres with the schema from Section 9.
2. **Build AI generation layer** -- query generation, rubric generation, and email prompt generation functions. Test against Chox as reference. This is the highest-leverage new code because it unlocks generalization.
3. **Create `ClientConfig` dataclass + Fernet encryption** -- foundational multi-tenancy.
4. **Parameterize pipeline modules** -- refactor `discover.py`, `score_leads.py`, `email_generator.py`, `github_client.py` to accept `ClientConfig`.
5. **Build self-serve onboarding flow** -- Stripe Checkout → Clerk auth → product context form → AI generation preview → dry run → credential input → go live. This is the product. No admin CLI, no manual setup.
6. **Build dashboard** -- leads table, email queue with auto-send, pipeline stats, settings. Clients need to be able to see what's happening without contacting you.
7. **Set up Celery scheduler + auto-send** -- automated daily runs per client, 24-hour auto-send on email queue.
8. **Onboard Chox as Client 0** -- full self-serve flow end-to-end.
9. **Marketing site + launch** -- landing page, pricing, Stripe coupon for founding customers. Use Ghostline on itself to find dev-tool founders. Go live.

The dashboard and self-serve onboarding are not "Phase 2" -- they ARE the product. Ship them before accepting any clients.

---

### Key Files to Refactor

| File | Change |
|---|---|
| `shared/config.py` | Extract all hardcoded globals into `ClientConfig` dataclass that loads from Postgres |
| `score_leads.py` | `SYSTEM_PROMPT` becomes per-client `scoring_rubric` loaded from `client_configs`; core scoring loop becomes reusable function accepting `ClientConfig` |
| `outreach/email_generator.py` | Replace hardcoded `CHOX_CONTEXT.md` load with dynamic prompt construction from `config.email_context_doc` |
| `discovery/github_client.py` | `__init__` accepts `github_token` parameter instead of reading from global config |
| `discovery/discover.py` | `discover_repos()` accepts `ClientConfig`, iterates over `config.search_queries` |
| `outreach/outreach_graph.py` | Add `client_config` to `OutreachState`; all nodes read from state |
| `outreach/outreach_state.py` | Add `client_config` field to `OutreachState` TypedDict |

---

*Generated: 2026-03-23*
