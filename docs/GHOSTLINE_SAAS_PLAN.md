# Ghostline SaaS — Business & Technical Plan

## Executive Summary

Ghostline is a working, opinionated GitHub-native lead generation and AI-powered outreach engine. The pipeline — discover, qualify, score, personalize, review, send, write-back — is already proven. The SaaS transformation is fundamentally a multi-tenancy and automation problem layered on top of that working core, not a rebuild.

**Goal**: $10k/month MRR serving dev-tool companies who need to reach developers.

**Differentiator**: Every competing tool (Apollo, Hunter, Instantly) uses job-title databases or LinkedIn scrapes. Ghostline uses GitHub — finding developers by what they are *actively building right now*, not who they say they are on a resume. No other SMB-priced tool does this end-to-end.

---

## Market Research

### Market Size

The lead generation software market sits at $7.4B in 2025, growing to $16.2B by 2034 (9.1% CAGR). The sales intelligence market is $4.85B in 2025, projected at $10.25B by 2032. Developer tooling specifically is a $6.4–7.6B market growing at 16% CAGR, with 550+ devtool companies mapped in the 2025 DevTools Landscape report. GitHub itself reported 130M+ active developers as of 2025.

**Conservative SAM for GitHub-native outreach**: Even placing 5,000–10,000 devtool companies paying $300–$600/month yields an $18M–$72M/year serviceable market — and the category is nascent with no dominant SMB player.

### Direct Competitors (GitHub-Native)

**Reo.dev** — Raised $4M seed in October 2025. Tracks 625M+ developer activity signals including GitHub interactions, package installs, and open-source telemetry. Customers include LangChain, N8N, Chainguard. However, Reo.dev is a *signal intelligence layer*, not an outreach tool. It identifies who is showing intent but does not automate personalized cold campaigns. It also requires companies to have existing product adoption to analyze — targeting companies with traction, not companies seeking net-new leads.

**Common Room** — Signal intelligence with 50+ source integrations including GitHub. Contracts start at $15,000/year ($1,000–6,500/month). Community-first, not outbound-first. Completely out of reach for pre-Series A devtool startups.

**No known tool** combines all four of: (1) GitHub as a primary lead source, (2) contact enrichment for those developers, (3) AI-personalized outreach referencing real technical context, and (4) SMB-accessible pricing. This is the gap Ghostline fills.

### Adjacent Competitors (Outreach Tools Without GitHub)

| Tool | GitHub signals | Developer personas | Outreach automation | SMB pricing |
|---|---|---|---|---|
| Apollo.io ($49–99/user/mo) | No | Partial (title only) | Yes | Yes |
| Hunter.io ($34+/mo) | No | No | No | Yes |
| Lemlist ($69+/user/mo) | No | No | Yes | Yes |
| Instantly.ai ($37–97/mo) | No | No | Yes | Yes |
| Outreach.io ($100–160/user/mo) | No | No | Yes | No |
| Common Room ($1,000+/mo) | Yes (signal only) | Yes | No | No |
| Reo.dev (custom pricing) | Yes (signal only) | Yes | No | Partial |

**Key weakness of Apollo**: 65–70% data accuracy, no GitHub signals, developer personas identified by job title only. Emails frequently hit spam. Generic outreach disconnected from the developer's actual technical work.

### GTM Channels for Reaching Devtool Companies

**Tier 1 (highest signal):**
- **Hacker News (Show HN)** — Single highest-leverage launch channel for developer tools. Educational posts with genuine utility generate hundreds of qualified inbound leads within 24–48 hours.
- **Product Hunt** — Best for first-mover visibility to tech-forward early adopters. Most valuable as a discovery channel.
- **YC network** — YC has backed 480+ devtool companies. Being visible to alumni via the network or direct outreach reaches a concentrated ICP.

**Tier 2 (community):**
- Dev.to / Hashnode written content
- Reddit (r/devops, r/startups, r/sideprojects)
- Discord/Slack communities (Developer Marketing Alliance, Heavybit)

**Tier 3 (outbound):**
- **Use Ghostline on itself** — find devtool founders on GitHub and run outreach. Most credible GTM motion and a live product demo.
- Developer conferences (DevRelCon, GitHub Universe, KubeCon)

---

## Business Model

### Pricing Tiers

**Starter — $299/month**
- 1 GitHub search campaign (single ICP)
- Up to 200 leads discovered/month
- Up to 60 emails sent/month (2/day, ramped)
- Dashboard: leads table, email status, pipeline stats
- Client's own Gmail + app password
- 1 custom email prompt configured at onboarding

**Growth — $599/month**
- Up to 3 concurrent campaigns (3 distinct ICPs or frameworks)
- Up to 600 leads discovered/month
- Up to 150 emails sent/month (5/day)
- Dashboard with lead scoring, email preview, campaign analytics
- 30-minute onboarding call to configure queries and email prompt

**Scale — $1,199/month**
- Unlimited campaigns
- Up to 1,500 leads/month
- Up to 300 emails/month (10/day)
- Slack/email digest of new leads and daily send summary
- Dedicated Slack channel for prompt iteration and support
- Weekly pipeline review, quarterly ICP refresh

**Annual discount**: 20% off for annual prepay (e.g., $5,750/year for Growth). Improves cash flow, reduces churn risk.

### Path to $10k MRR

| Scenario | Clients | Mix | MRR |
|---|---|---|---|
| All Growth | 17 | 17 × $599 | $10,183 |
| Mixed | 16 | 8 × $299 + 5 × $599 + 3 × $1,199 | $10,184 |
| Scale-anchored | 9 | 1 × $599 + 8 × $1,199 | $10,191 |

**Practical target**: 10 Growth clients (~$6k MRR) + 3 Scale clients to cross $10k. Achievable in 6–9 months from first paying client.

---

## MVP Scope

### What to Build First

The MVP is the smallest thing that lets you take on a paying client without embarrassing yourself. You do not need a polished dashboard or self-serve onboarding to charge the first $299.

**MVP (4–6 weeks part-time):**

1. **Multi-tenant config layer** — A database table (or per-client JSON config for week 1) holding per-client: search queries, email context doc, SMTP credentials, Google Sheet ID, GitHub token
2. **Scheduled automation** — Cloud-hosted scheduler runs each client's pipeline daily, no manual triggering
3. **Per-client data isolation** — Each client writes to their own Google Sheet; credentials stored encrypted
4. **Per-client email prompts** — The system prompt and product context (currently `CHOX_CONTEXT.md`) become per-client config fields loaded at runtime
5. **Manual onboarding** — You set up each client by hand: 30–60 minutes per client, fine for the first 10

**Defer to Phase 2:**
- Self-serve signup and web onboarding
- Full React dashboard
- Stripe billing integration
- Automated client provisioning
- Follow-up sequences
- Reply tracking

**The minimum to charge**: Parameterize config for per-client values, deploy to a cloud VPS on a schedule, store credentials securely. You can run the first 2–3 clients manually while building the multi-tenant layer.

---

## Technical Architecture

### Overview

Three layers: the pipeline engine (existing Python code, minimal changes), a multi-tenant orchestration layer (new), and a web dashboard (new).

```
[Web Dashboard]            [Admin CLI]
        |                       |
[Orchestration: Client Registry + Job Scheduler]
        |
[Per-Client Pipeline Runner]
  client_id → ClientConfig → runs pipeline
        |
[Existing Pipeline Modules]
  discover → qualify → score → outreach graph
        |
[Per-Client Isolated Storage]
  PostgreSQL (leads, runs, emails) + Client's Google Sheet
```

### Multi-Tenancy Model

**Database tables (PostgreSQL):**

```
clients
  id (uuid), name, slug, plan, status, created_at

client_configs
  client_id (fk)
  github_token_enc          — encrypted
  smtp_username
  smtp_password_enc         — encrypted
  anthropic_api_key_enc     — encrypted (or use a central key)
  sender_name, sender_email
  spreadsheet_id
  service_account_json_enc  — encrypted
  search_queries            — jsonb array of GitHub query strings
  email_context_doc         — per-client equivalent of CHOX_CONTEXT.md
  batch_size, max_emails_per_day
  tier1_threshold, tier2_threshold
  custom_blocklists         — jsonb, additive overrides to global blocklists
  icp_description           — human-readable, internal reference

pipeline_runs
  id, client_id, started_at, finished_at, status
  repos_discovered, leads_added, emails_sent, errors (jsonb)

leads
  id, client_id, github_username, email, full_name
  repo_url, repo_name, repo_stars, lead_score, lead_tier
  frameworks_detected, profile_company
  contacted (bool), contacted_at, response_status, discovered_at

email_drafts
  id, client_id, lead_id, subject, body
  status (pending/approved/sent/bounced/rejected)
  sent_at, send_error
```

All encrypted fields use Fernet symmetric encryption (`cryptography` library). The key lives in the app's environment, never in the database.

### Pipeline Parameterization

The core change: replace module-level globals with a `ClientConfig` dataclass passed into every pipeline function.

**Before (current):**
```python
# shared/config.py reads from .env
SEARCH_QUERIES = [...]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
```

**After (SaaS):**
```python
@dataclass
class ClientConfig:
    client_id: str
    search_queries: list[str]
    github_token: str
    smtp_username: str
    smtp_password: str
    email_context_doc: str
    max_emails_per_day: int
    batch_size: int
    # ... all other per-client params

def discover_repos(client: GitHubClient, config: ClientConfig) -> list[dict]:
    for query in config.search_queries: ...
```

`email_generator.py` currently loads `CHOX_CONTEXT.md` from disk at import time. In the SaaS version the system prompt is built dynamically at call time from `config.email_context_doc`.

`OutreachState` gains a `client_config: ClientConfig` field so all LangGraph nodes read from state rather than globals.

### Key Files to Refactor

| File | Change |
|---|---|
| `shared/config.py` | Extract all hardcoded globals into `ClientConfig` dataclass |
| `discovery/discover.py` | Accept `config: ClientConfig`, use `config.search_queries` |
| `outreach/email_generator.py` | Build system prompt dynamically from `config.email_context_doc` |
| `outreach/outreach_graph.py` | Add `client_config` to `OutreachState`; nodes read from state |
| `outreach/outreach_state.py` | Add `client_config` field to `OutreachState` TypedDict |
| `outreach/outreach_config.py` | Convert to `ClientOutreachConfig` dataclass derived from `ClientConfig` |

### Scheduling and Automation

**Recommended**: Celery + Redis on a single VPS (Hetzner CX21, ~$6/month).

- Celery Beat triggers `run_pipeline_for_client(client_id)` for each active client daily, staggered by 30 minutes to distribute GitHub API load
- Each task loads `ClientConfig` from Postgres, instantiates `GitHubClient` with client's token, runs the full pipeline
- Redis is the broker (Upstash free tier works for MVP)

**Phase 1 alternative**: GitHub Actions matrix strategy — one workflow per client on a schedule, config loaded from Actions secrets. Free for small client counts. Migrate to Celery at 5+ clients.

**Example stagger (10 clients):**
```
Client 1: 06:00 UTC daily
Client 2: 06:30 UTC daily
Client 3: 07:00 UTC daily
...
```

**Human-in-the-loop in SaaS context**: The current terminal review (A/R/E/B/Q) is incompatible with fully automated SaaS. For Phase 1, you review and approve all client emails before they send (ensures quality, costs your time). For Phase 2, the web dashboard provides a review UI replacing the terminal CLI.

### Web Dashboard — Recommended Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui | Professional dashboard UI in hours, zero-config Vercel deploy |
| Backend API | FastAPI (Python) | Same language as pipeline, async-first, automatic OpenAPI docs |
| Database | PostgreSQL (Supabase or Railway managed) | Reliable, integrates with everything |
| Auth | Clerk (magic link or Google OAuth) | Zero password management, works in minutes |
| Hosting (frontend) | Vercel (free tier) | Zero-config, global CDN |
| Hosting (backend) | Render or Railway | Simple Python deployment |
| Job queue | Celery + Redis (Upstash free tier) | Native Python, reliable scheduling |

**Dashboard pages (Phase 2):**
1. **Leads table** — paginated, filterable by tier/contacted/score, sortable
2. **Pipeline runs** — per-campaign history with stats (repos found, leads added, emails sent)
3. **Emails sent** — subject, recipient, sent_at, status
4. **Review queue** — pending email drafts with approve/reject UI (replaces terminal CLI)
5. **Campaign config** — read-only view of search queries and ICP description
6. **Settings** — SMTP status, plan, usage vs limit

### Data Isolation

Three levels:

1. **Database**: Every table has `client_id` FK. All queries scoped `WHERE client_id = ?`. No cross-client queries.
2. **Google Sheets**: Each client has their own `spreadsheet_id` in `client_configs`.
3. **Email sending**: Each client's SMTP credentials stored encrypted, used exclusively for their outreach.
4. **LangGraph checkpoints**: Per-client checkpoint files (`ghostline_outreach_{client_id}.db`) or Postgres-backed LangGraph checkpointer.

---

## Search Expansion Strategy

The current `SEARCH_QUERIES` is hardcoded for LangChain/LangGraph. `client_configs.search_queries` becomes a JSON array of GitHub query strings crafted per client during onboarding.

### Query Examples by ICP

**"Developers using Stripe API in Python agents":**
```
stripe language:python pushed:>2025-01-01 fork:false
stripe+agent language:python pushed:>2025-01-01 fork:false
"stripe.Charge.create" language:python pushed:>2025-01-01 fork:false
```

**"React developers building fintech apps":**
```
react+plaid language:typescript pushed:>2025-01-01 fork:false
react+stripe language:typescript pushed:>2025-01-01 fork:false
"usePlaidLink" pushed:>2025-01-01 fork:false
```

**"Developers using Pinecone":**
```
pinecone language:python pushed:>2025-01-01 fork:false
"from pinecone import" language:python pushed:>2025-01-01 fork:false
```

### Configurable Scoring

`TIER_A_IMPORTS`, `TIER_B_IMPORTS`, `TIER_C_IMPORTS` in `shared/config.py` are currently LangChain-specific. Each client config stores equivalent tier arrays for their target technology as JSON. You define these during onboarding; a Phase 2 UI exposes them to clients.

### Blocklist Customization

Global blocklists (`REPO_NAME_BLOCKLIST`, `DESCRIPTION_BLOCKLIST`) remain as defaults with per-client additive overrides stored in `client_configs.custom_blocklists`.

### Code Search Verification

`github_client.py` already has `search_code()`. For clients with specific import patterns, add an optional post-discovery code-search step confirming the exact import exists before scoring. Costs 1 extra API call per repo but dramatically improves precision for narrow ICPs.

---

## Client Onboarding

### Phase 1: Assisted Onboarding (White-Glove)

Every new client gets a 45-minute onboarding call. This is intentional — it justifies pricing, ensures quality, and teaches you what to automate later.

**Pre-call homework sent to client:**
- Create or identify the Gmail they'll send from; enable 2FA; generate an app password
- Get an Anthropic API key (or you supply centrally — see cost section)
- Write a brief ICP doc: who do they want to reach, what frameworks does that developer use, what problem does their product solve

**Onboarding call (45 min):**
1. Review ICP doc, clarify target developer profile (10 min)
2. Design search queries together, test 2–3 live on GitHub.com to validate quality (15 min)
3. Write email context doc: product description, value prop, tone, CTA (15 min)
4. Collect credentials: Gmail app password, GitHub token, Google Sheet ID (5 min)

**Post-call by you (30 min):**
1. Create client record in database
2. Configure `ClientConfig`
3. Set up Google Sheet with correct headers
4. Run dry-run pipeline, share sample leads with client
5. Enable scheduled pipeline

**Retention**: Send a weekly digest email (automated) showing last week's pipeline stats — leads discovered, emails sent, response rate. Keeps clients engaged between logins.

### Phase 2: Self-Serve Onboarding

After 5–10 clients, partially automate:

1. Stripe Checkout → client selects plan, enters email
2. Magic link auth → client lands in dashboard
3. ICP wizard → target technology (dropdown + custom), developer type, product description
4. Query preview → system suggests 3–5 queries, client edits
5. Credential input → Gmail SMTP + GitHub token with live validation
6. Email context draft → Claude pre-populates from product description, client reviews
7. Dry run → system runs 10-repo preview, shows sample leads in dashboard
8. Go live → client clicks "Start Pipeline", first run within 24 hours

---

## GTM and Client Acquisition

### First 10 Clients Strategy

**Step 1: First 3 clients — manual outreach, pilot pricing (weeks 1–4)**

Do not build anything new. Find 3 companies manually and offer a 30-day pilot at $149/month (founding customer price). Goal: paying commitment + honest feedback.

Where to find them:
- Product Hunt launches (last 90 days, tagged "Developer Tools" or "API")
- YC current and last 2 batches — devtool companies
- Indie Hackers "Show IH" posts where the product is a dev-tool
- Twitter/X: search `"we just launched our API"` or `"our SDK is live"` by founders in the last 30 days

**Pitch (DM or cold email):**
> "I built a tool that finds developers on GitHub who are actively building with [their SDK/framework] and sends them personalized cold emails on your behalf. Looking for 3 early customers to pilot it for $149/month. Want a demo?"

**Step 2: Scale to 10 clients (months 2–4)**

**Channel 1: Use Ghostline on itself.** Find devtool founders on GitHub. Send personalized emails referencing their actual repo. Your pitch: "I used my own tool to find you — here's what Ghostline surfaced about your project. Want to see it in action for your company?" This is the most credible GTM motion and a live product demo in every email.

**Channel 2: Hacker News Show HN.** Once you have 3+ clients with measurable results (reply rates, demos booked), post a detailed "how I built this" — the GitHub-native outreach angle is genuinely interesting to the HN audience. No pitching; purely educational. Include the technical architecture. HN is the single highest-leverage channel for developer tools.

**Channel 3: Indie Hackers.** Post monthly progress updates: "Month 1: 0 clients. Month 2: 3 clients at $149. Here's what worked." The IH audience includes devtool founders who are your exact ICP.

**Channel 4: Product Hunt.** Launch once you have a working dashboard. Time for mid-week. Coordinate with early clients for initial upvotes. Aim for #3–5 in Developer Tools.

**Channel 5: Content.** One blog post per month on topics devtool founders search for:
- "How to find developers using your SDK on GitHub"
- "Cold email to developers: what actually works (with data)"
- "GitHub API for lead generation: a practical guide"

These compound over time. Low volume at first, free forever.

### Pricing for GTM

**Founding customer pricing** for first 5 clients: $199/month for Growth (vs. $599 list). 90-day trial. Creates committed early customers and real testimonials. Move to published pricing after 5 paying clients.

### Success Metrics

- Leads discovered/month per client
- Email send rate (sent / discovered)
- Reply rate (replies / sent) — target 3–8% for cold developer outreach
- Client MRR by month
- Churn (first signal usually month 2 if pipeline output is poor)

---

## Operational Considerations

### GitHub API Rate Limits

Each discovery run uses ~18 search API calls + ~400 core API calls per 100 leads.

With 10 clients staggered over 10 hours: 10 × 18 = 180 search calls/day = 18/hour, well within 30/min limit. Core API: 10 × 400 = 4,000 calls/day. Fine if staggered; tight if all run simultaneously.

**Solution**: Each client provides their own GitHub PAT (no scopes, public data only). Each token gets its own 5,000 core calls/hour budget. Maintain a pool of 5–10 Ghostline-owned tokens as fallback. At 5 tokens, effective capacity is 25,000 calls/hour.

### Gmail Sending Limits

Gmail SMTP: 500 emails/day per personal account, 2,000/day for Google Workspace. Each client sends ≤20/day — well within limits. Each client uses their own account so there is no shared sending limit.

**Warm-up automation**: Implement a `warm_up_schedule` in `client_configs` that automatically manages the ramp-up (5/day weeks 1–2, 10/day weeks 3–4, 15–20/day week 5+). The pipeline checks this at runtime and applies the correct limit.

**Bounce monitoring**: If a client's bounce rate exceeds 5% in a week, automatically pause their pipeline and alert them.

### Anthropic API Costs

~$0.015 per email at Claude Sonnet pricing.

| Scale | Emails/month | Claude cost |
|---|---|---|
| 10 clients × 20/day | 6,000 | ~$90/month |
| 25 clients × 20/day | 15,000 | ~$225/month |

At $10k MRR: ~$225/month in Claude costs. Gross margin ~97%.

**Recommendation**: Maintain one central Anthropic API key for MVP. Absorb the cost — it's negligible. Revisit at 50+ clients if needed.

### Estimated Monthly Infrastructure Cost

| Item | Cost |
|---|---|
| VPS (Hetzner CX21: 2 vCPU, 4GB RAM) | $6/month |
| Managed Postgres (Supabase free tier) | $0–10/month |
| Redis (Upstash free tier) | $0–5/month |
| Anthropic API (10 clients × 20 emails/day) | ~$90/month |
| Vercel (frontend) | $0 |
| Render (FastAPI backend) | $0–7/month |
| **Total at 10 clients** | **~$100–120/month** |

**Gross margin at $6k MRR: ~98%.**

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| **GitHub API policy changes** | Use authenticated tokens only, stay within rate limits, graceful degradation already built in. Monitor GitHub changelog. |
| **Gmail deliverability / spam** | Enforce warm-up schedule, monitor bounce rates per client, auto-pause high-bounce clients, recommend Google Workspace for serious senders. |
| **Solo founder bandwidth at scale** | Automate monitoring aggressively (pipeline digest emails, error alerts on exception). Hire part-time client success contractor at $5k+ MRR. |
| **Client churn from poor lead quality** | Set expectations at onboarding (3–8% reply rates are normal). Show dry-run sample before client pays. Offer month-1 satisfaction credit if <50 leads + <30 emails sent. |
| **Anthropic API dependency** | `email_generator.py` is cleanly isolated. Abstract the LLM call behind an `LLMProvider` interface now — OpenAI or other providers are a drop-in replacement. |
| **Competition from Apollo, Reo.dev** | The moat is GitHub-native discovery + README-level personalization + per-client ICP tailoring. Position explicitly against "generic outreach databases." |

---

## Phased Roadmap

### Phase 1 — MVP to First Paying Client (Weeks 1–8)

**Goal**: One paying client, pipeline running reliably without manual babysitting.

| Week | Work |
|---|---|
| 1–2 | Deploy codebase to VPS. Set up Postgres. Create `clients` and `client_configs` tables. Implement `ClientConfig` dataclass with Fernet encryption for sensitive fields. |
| 3–4 | Parameterize pipeline: refactor `discover.py`, `email_generator.py`, `outreach_graph.py` to accept `ClientConfig`. Add `client_config` to `OutreachState`. |
| 5 | Implement Celery + Redis scheduler. Create `run_pipeline_for_client(client_id)` task. Set up staggered daily schedule. |
| 6–7 | Sign first client. Run assisted onboarding. Configure their `ClientConfig` in the database. Run dry-run, share results. Enable live pipeline. |
| 8 | Monitor first client's pipeline for one full week. Fix bugs. Document manual onboarding process. |

---

### Phase 2 — Scale to $10k MRR (Months 3–9)

**Goal**: 15–20 paying clients, mostly self-running, basic web dashboard.

| Month | Work |
|---|---|
| 3–4 | Dashboard v1: Next.js + FastAPI + Clerk auth. Leads table, pipeline run history, emails sent log. Per-run stats to `pipeline_runs` table. Dual-write leads to Postgres + Google Sheets. Web-based email review UI replacing terminal CLI. |
| 4–5 | Stripe Checkout integration. Partial self-serve onboarding wizard: ICP form, query preview, credential input, email context draft, auto-provisioning on successful payment. |
| 5–7 | Show HN post once you have 3+ clients with measurable results. Product Hunt launch. Begin cold outreach to YC devtool companies using Ghostline itself. 1 blog post/month. |
| 7–9 | Follow-up sequences (2-touch: initial + 1 follow-up after 5 days if no reply). Slack digest per client (weekly send summary via webhook). A/B prompt testing (2 email context variants, Ghostline alternates and reports performance). |

---

### Phase 3 — Growth (Month 9+, if going full-time)

**Goal**: $25k+ MRR, first hire, product-led growth.

- Fully automated self-serve onboarding including Claude-generated queries from ICP description
- Public marketing site and pricing page
- Client case studies (reply rates, demos booked, closed deals attributed to Ghostline)
- API access for Scale clients: programmatic lead export, webhook on new leads
- CRM integrations (HubSpot, Pipedrive): new leads pushed directly to client's CRM
- Multi-channel outreach: LinkedIn DM as optional additional channel
- First hire: part-time customer success contractor for onboarding and client communication
- White-label offering for developer marketing agencies

---

## Immediate Next Steps (This Week)

In priority order — validate before building:

1. **Find first client informally** (pre-product, pilot pricing) — validate that anyone will pay before writing more code
2. **Deploy existing codebase to a VPS** — get infrastructure running
3. **Create `ClientConfig` dataclass and database tables** — foundational multi-tenancy change
4. **Parameterize `discover.py`, `email_generator.py`, `outreach_graph.py`** — core pipeline refactor
5. **Set up the scheduler** — first client's pipeline runs daily without you touching it
6. **Run first client through a full cycle** — find real bugs, tune for their ICP
7. **Charge them**

Everything else — dashboard, self-serve onboarding, Stripe, full web app — comes after you have a repeatable manual process working for 3 clients.

---

*Generated: 2026-03-19*
