# Ghostline Phase 2: LangGraph Email Outreach Agent — Implementation Plan

## 1. Executive Summary

The Ghostline outreach agent is a LangGraph-based workflow that reads scored developer leads from the Phase 1 Google Sheet, fetches each lead's GitHub repo README, uses Claude to generate a personalized cold email connecting their specific project to Chox's governance capabilities, presents batches of emails for human review, and sends approved emails via Outlook.com SMTP. The entire pipeline — from sheet read to email send to status writeback — is orchestrated as a stateful LangGraph graph with a human-in-the-loop checkpoint gate between generation and sending.

---

## 2. LangGraph Architecture

### 2.1 Why LangGraph

LangGraph is the right choice for this workflow because:

- **Stateful workflow with persistence**: The pipeline must pause between email generation and human approval, potentially for hours. LangGraph's checkpoint system persists state across interruptions natively.
- **Conditional branching**: Different paths based on approval status (send vs. reject vs. edit), README fetch success/failure, and email send success/failure.
- **Retry logic**: Failed sends, API rate limits, and transient errors need structured retry without re-running the entire pipeline.
- **Batch processing with breakpoints**: LangGraph's `interrupt_before`/`interrupt_after` mechanism maps directly to the human approval gate.

### 2.2 State Graph Nodes

| Node | Purpose |
|------|---------|
| `load_leads` | Read uncontacted leads from Google Sheet (contacted == "FALSE") |
| `fetch_readmes` | For each lead, fetch the repo README from GitHub API |
| `generate_emails` | Call Claude API to generate personalized email for each lead |
| `present_for_review` | Format batch for human review; checkpoint/interrupt here |
| `process_approval` | Parse human decisions (approve/reject/edit per email) |
| `send_emails` | Send approved emails via Outlook.com SMTP with pacing |
| `update_sheet` | Write back contacted=TRUE, contacted_at, contact_method, notes |
| `report` | Print summary stats for the run |

### 2.3 State Graph Diagram

```
START
  |
  v
[load_leads] --(no leads)--> END
  |
  v
[fetch_readmes]
  |
  v
[generate_emails]
  |
  v
[present_for_review]  <<<--- INTERRUPT (human-in-the-loop)
  |
  v
[process_approval] --(all rejected)--> [update_sheet] --> [report] --> END
  |
  (has approved)
  |
  v
[send_emails]
  |
  v
[update_sheet]
  |
  v
[report]
  |
  v
END
```

### 2.4 Human-in-the-Loop Checkpoint

The checkpoint is placed using LangGraph's `interrupt_before=["process_approval"]` configuration. When the graph reaches `present_for_review`, it outputs the batch to the console and halts. The operator reviews, provides approval decisions, and the graph resumes from the checkpoint with the human input injected into state.

---

## 3. Email Sending Infrastructure

### 3.1 Option Evaluation

| Option | Cost | Daily Limit | Auth Complexity | Verdict |
|--------|------|-------------|-----------------|---------|
| Outlook.com SMTP | Free | 300 emails/day | App password or OAuth2 | **Recommended** |
| Microsoft Graph API | Free | 10,000/day for personal | OAuth2 + Azure app registration | Over-engineered for this volume |
| SendGrid Free Tier | Free (100/day) | 100 emails/day | API key | Too low, and adds third-party sender |
| Mailgun Free Tier | Free (100/day for 3 months) | 100 emails/day | API key + domain verification | Too low |

### 3.2 Recommendation: Outlook.com SMTP

For low-volume personalized outreach (10-30 emails/day target), Outlook.com SMTP is the optimal choice:

- **Cost**: Free (included with any Outlook.com/Hotmail account)
- **Daily limit**: 300 recipients/day (more than enough)
- **Per-message limit**: 100 recipients (irrelevant for 1:1 emails)
- **Authentication**: SMTP with OAuth2 or app-specific password
- **Server**: `smtp-mail.outlook.com`, port 587, STARTTLS
- **Sender identity**: Emails come from your actual Outlook.com address — SPF/DKIM are handled by Microsoft automatically

### 3.3 Authentication Setup

Since Microsoft disabled basic auth for SMTP in 2023, you need one of:

**Option A — App Password (simpler):** If the Outlook.com account has 2FA enabled, generate an "app password" at https://account.live.com/proofs/manage. This allows traditional SMTP AUTH without OAuth2 complexity. **This is the recommended path for a personal project.**

**Option B — OAuth2:** Register an app in Azure AD (free tier), grant `SMTP.Send` delegated permission, use the MSAL library to obtain an OAuth2 access token, pass it to `smtplib` via `AUTH XOAUTH2`.

### 3.4 SMTP Configuration

```
SMTP_HOST = "smtp-mail.outlook.com"
SMTP_PORT = 587
SMTP_USE_TLS = True  (STARTTLS)
SMTP_USERNAME = <outlook email>
SMTP_PASSWORD = <app password or OAuth2 token>
```

---

## 4. Deliverability Strategy

### 4.1 Send Volume and Pacing

**Target volumes** (conservative for a personal Outlook.com account):

| Period | Emails | Rationale |
|--------|--------|-----------|
| Week 1-2 (warm-up) | 5/day | Build sender reputation gradually |
| Week 3-4 | 10/day | Increase after no bounces |
| Week 5+ (steady state) | 15-20/day | Sustainable for personal Outlook.com |
| Hard ceiling | 30/day | Never exceed; stay well under 300 limit |

**Pacing between sends**:
- Minimum 90 seconds between emails (randomized 90-180 seconds)
- Never send more than 5 emails within any 30-minute window
- Send during business hours (9am-5pm recipient local time, or 9am-5pm ET as default)
- Avoid Mondays before 10am and Fridays after 2pm (lowest open rates)

**Implementation**: The `send_emails` node applies `time.sleep(random.uniform(90, 180))` between each SMTP send.

### 4.2 Warm-Up Schedule

| Week | Daily Volume | Notes |
|------|-------------|-------|
| 1 | 3-5 | Send to highest-quality leads first (tier_1, high scores). Higher engagement rates build reputation. |
| 2 | 5-8 | Monitor for bounces. If bounce rate > 5%, stop and investigate. |
| 3 | 8-12 | Expand to tier_2 leads. |
| 4 | 12-15 | Steady state if no deliverability issues. |
| 5+ | 15-20 | Maintain. Never spike volume. |

### 4.3 Email Format Best Practices

**Plain text only.** No HTML.

Rationale: Cold outreach emails with HTML (images, styled text, tracking pixels) are flagged by spam filters at significantly higher rates. Plain text emails look like genuine 1:1 correspondence. They also render consistently across all email clients.

**Subject line patterns** (cold outreach best practices):
- Short: 3-7 words
- Lowercase (except proper nouns) — looks informal/personal, not marketing
- Reference their project or technology by name
- No exclamation marks, no ALL CAPS, no emojis
- No "Re:" or "Fwd:" deception

Examples:
- `quick question about {repo_name}`
- `saw your {framework} agent project`
- `governance for {repo_name}`
- `{first_name} - agent safety for {framework} projects`

**Email length**:
- Maximum 150 words (ideally 100-130)
- 5-7 sentences across 3-4 short paragraphs
- No walls of text

**CTA style**:
- Single, low-friction CTA
- Ask a question, not a commitment: "Would it be useful to see how this works on a project like yours?"
- Never "Schedule a demo" or "Book a call" in a first touch

**Signature format**:
```
— Fayzan & Dilraj
Co-founders, Chox (chox.ai)
```

No images, no social links, no legal disclaimers in signature (keep it minimal).

### 4.4 CAN-SPAM Compliance

Required elements in every email:

1. **Accurate "From" header**: Must identify Fayzan/Dilraj and Chox
2. **No deceptive subject line**: Subject must relate to email content
3. **Physical postal address**: Include a valid physical address (can be a PO Box or registered agent address). This goes in the email footer.
4. **Unsubscribe mechanism**: Every email must include a way to opt out (see 4.6)
5. **Honor opt-outs within 10 business days**: The system must track unsubscribes and exclude those leads from future sends
6. **Identify as advertisement**: Since these are targeted 1:1 outreach (not bulk), including the unsubscribe link and physical address is sufficient.

### 4.5 SPF/DKIM/DMARC for Outlook.com

When sending from an `@outlook.com` or `@hotmail.com` address:

- **SPF**: Microsoft's SPF record already covers `smtp-mail.outlook.com`. No action needed.
- **DKIM**: Microsoft signs outgoing Outlook.com emails with DKIM automatically. No action needed.
- **DMARC**: Microsoft publishes DMARC for `outlook.com`. No action needed.

If using a custom domain in the future, you would need to configure SPF/DKIM/DMARC DNS records. For now, sending from `@outlook.com` inherits Microsoft's full email authentication stack.

### 4.6 Unsubscribe Mechanism

Every email must include an unsubscribe line at the bottom:

```
If you'd rather not hear from us, reply "unsubscribe" and we'll remove you immediately.
```

Why reply-based instead of a link:
- No need to build/host an unsubscribe landing page
- Reply-based unsubscribes actually improve deliverability (replies signal to inbox providers that this is real correspondence)
- Simple to implement: check for "unsubscribe" in reply subject/body during manual response monitoring

The system tracks unsubscribed users by setting `response_status = "unsubscribed"` in the Google Sheet. The `load_leads` node filters these out.

### 4.7 Reply-To Setup

Set the `Reply-To` header to the same Outlook.com address used for sending. This ensures replies go to a monitored inbox. Do NOT use a `noreply@` address.

---

## 5. Email Personalization Engine

### 5.1 System Prompt Design

The Claude API call uses a system prompt that provides:

1. The Chox product context (loaded from `CHOX_CONTEXT.md`)
2. The email writing constraints (length, tone, structure)

```
System prompt structure:

You are a cold email copywriter for Chox, an AI agent governance layer.
You write short, personalized outreach emails to developers who are building
AI agents that call external APIs.

PRODUCT CONTEXT:
{contents of CHOX_CONTEXT.md, truncated to key sections}

EMAIL CONSTRAINTS:
- Maximum 150 words, 5-7 sentences
- Plain text only, no markdown formatting
- First paragraph: Reference their specific project and what it does (1-2 sentences).
  Personalize based on their repo README — what they're building, what frameworks
  they use, what their agent does. This is the primary personalization vector.
- Second paragraph: Connect what they're building to Chox's core value prop —
  governance and visibility over agent tool calls. Keep it concrete: classify,
  risk-score, shadow verdicts, two-line integration. (2-3 sentences)
- Third paragraph: Low-friction CTA question (1 sentence)
- Sign off: "— Fayzan & Dilraj\nCo-founders, Chox (chox.ai)"
- Footer: Physical address + unsubscribe line
- Tone: Casual, technical peer-to-peer, not salesy
- Never use: "excited", "revolutionary", "game-changing", "leverage", "synergy"
- Never claim to know them personally
- Do not mention that you read their README or scraped their data
```

### 5.2 User Prompt (Per Lead)

```
Write a cold outreach email for this developer:

NAME: {full_name or github_username}
PROJECT: {repo_name} — {repo_description}
README SUMMARY: {first 2000 chars of README, or "README not available"}
FRAMEWORKS: {frameworks_detected}
COMPANY: {profile_company or "Independent"}

Generate:
1. SUBJECT: A short (3-7 word) subject line
2. BODY: The email body following the constraints above
```

Note: The `inferred_pain_point` and `risk_apis_detected` fields from the sheet are NOT passed to Claude. All leads share the same core pain point (building AI agents with tool access but no governance layer), so personalization comes entirely from what their repo README reveals about their specific project — not from a pain point category.

### 5.3 Example Emails

**Example 1: LangGraph multi-step agent**

```
Subject: governance for your langgraph pipeline

Hi Marcus,

I came across your agent-trading-bot project — looks like you're building
an autonomous multi-step pipeline with LangGraph that orchestrates several
external API calls per run.

We built Chox (chox.ai) to give developers visibility into what their agents
actually do at the API level. Every outbound call gets classified by action
type, risk-scored, and logged with a shadow verdict — so you can see what
would be blocked before flipping to enforcement. Two lines of SDK code to start.

Would it be useful to see how this works on a project like yours?

— Fayzan & Dilraj
Co-founders, Chox (chox.ai)

Chox, Inc. | [physical address]
Reply "unsubscribe" to opt out.
```

**Example 2: LangChain tool-calling agent**

```
Subject: saw your langchain agent project

Hi Priya,

Your data-analyst-agent project caught my eye — using LangChain to let an
agent query databases and generate reports is exactly the kind of use case
we think about every day.

We're building Chox (chox.ai), a governance layer that sits between your
agent and the APIs it calls. It classifies every tool call, scores risk,
and generates verdicts — all in shadow mode first so nothing changes until
you're ready. Works via SDK wrap or HTTP proxy.

Curious if you've thought about monitoring what your agent does once
it's running in production?

— Fayzan & Dilraj
Co-founders, Chox (chox.ai)

Chox, Inc. | [physical address]
Reply "unsubscribe" to opt out.
```

**Example 3: Minimal README / generic agent**

```
Subject: quick question about your agent project

Hi Chen,

I noticed your langchain-assistant project — looks like you're building a
tool-calling agent with several external API integrations.

We're working on Chox (chox.ai), a governance layer for AI agents. It
classifies every outbound API call your agent makes by action type and
risk, logs it with a shadow verdict, and gives you a path to enforcement
when you're ready. No agent code changes needed.

Have you thought about how you'd keep track of what your agent actually
does at the API level?

— Fayzan & Dilraj
Co-founders, Chox (chox.ai)

Chox, Inc. | [physical address]
Reply "unsubscribe" to opt out.
```

### 5.5 Tone Guidelines

- Write like a developer talking to a developer, not a marketer
- Be specific — mention their repo name, their framework, what they're building (from README)
- Assume they are smart and busy — no explaining what LangChain is
- Show, don't tell — describe what Chox does concretely, not abstractly
- One clear value proposition per email, not a feature dump
- No urgency tactics, no scarcity, no flattery beyond genuine project acknowledgment

---

## 6. Human-in-the-Loop Design

### 6.1 Batch Size: 10 emails

**Justification:**
- Small enough to review carefully (5-10 minutes of review time)
- Large enough to be productive (10 emails per batch, 2 batches per day = 20 emails)
- Aligns with daily send targets during warm-up (5-20/day)
- Each batch represents a natural unit of work: review, approve, send, confirm
- Keeps the review feedback loop tight — if Claude's tone drifts, you catch it within 10 emails

### 6.2 What the Reviewer Sees

For each email in the batch, the CLI displays:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email 3/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEAD CONTEXT:
  Name:       Marcus Chen
  Username:   mchen42
  Email:      marcus@tradingcorp.io
  Repo:       mchen42/agent-trading-bot (47 stars)
  Frameworks: langgraph, langchain
  Score:      38 (tier_1)
  Company:    TradingCorp

GENERATED EMAIL:
  Subject: agent governance for stripe integrations

  Hi Marcus,

  [... full email body ...]

ACTION: [A]pprove / [R]eject / [E]dit / approve [B]atch / [Q]uit
>
```

### 6.3 Reviewer Actions

| Key | Action | Behavior |
|-----|--------|----------|
| `A` | Approve | Mark this email as approved; advance to next |
| `R` | Reject | Mark as rejected; advance to next (lead stays uncontacted for future runs) |
| `E` | Edit | Open the email body in `$EDITOR` (e.g., vim/nano); save to approve edited version |
| `B` | Approve Batch | Approve all remaining emails in this batch |
| `Q` | Quit | Abort the run; no emails sent; state persisted for resume |

### 6.4 State Persistence

LangGraph's `SqliteSaver` checkpoints the full state — including generated emails, approval statuses, and lead data — at the interrupt point. If the operator quits, the next invocation can resume from the checkpoint without re-fetching READMEs or re-calling Claude.

Checkpoint storage: SQLite file at `ghostline_outreach.db` in the project root.

### 6.5 CLI Interface Design

The review step runs in the terminal. The `present_for_review` node formats all emails with lead context and writes them to stdout. The graph then interrupts. On resume, human decisions are passed via `graph.invoke(Command(resume=approval_decisions), config)`.

The review CLI is implemented as a standalone function called from the main run script, which collects decisions into a list of `{index, action, edited_body}` dicts and passes them back to the graph.

---

## 7. Google Sheets Integration

### 7.1 Reading Uncontacted Leads

Reuse `sheets.py`'s `connect_to_sheet()` for authentication. Add a new function:

```python
def load_uncontacted_leads(worksheet) -> list[dict]:
    """
    Read all rows where contacted == "FALSE" and email is non-empty.
    Returns list of dicts keyed by GOOGLE_SHEET_HEADERS, plus a 'row_number' field.
    Uses worksheet.get_all_records() for a single API call.
    Filters out response_status == "unsubscribed".
    """
```

### 7.2 Updating After Send

After sending each email, update the lead's row:

```python
def mark_lead_contacted(worksheet, row_number: int, method: str = "email", notes: str = ""):
    """
    Update columns: contacted=TRUE, contacted_at=<ISO timestamp>,
    contact_method=<method>, notes=<notes>
    Uses batch_update for efficiency.
    """
```

Column indices (1-indexed, matching `GOOGLE_SHEET_HEADERS`):
- Column 23 (`W`): `contacted` -> "TRUE"
- Column 24 (`X`): `contacted_at` -> ISO 8601 timestamp
- Column 25 (`Y`): `contact_method` -> "email"
- Column 27 (`AA`): `notes` -> e.g., "outreach_batch_2026-03-18, subject: saw your langgraph project"

### 7.3 Batch Read/Write

- **Read**: Single `get_all_records()` call to load all leads, filter in Python
- **Write**: Batch cell updates using `worksheet.batch_update()` — one API call for all row updates
- **Rate limiting**: Reuse existing `_retry_write()` with 429 backoff from `sheets.py`

### 7.4 Tracking Response Status

| Value | Meaning |
|-------|---------|
| `none` | Default, never contacted |
| `sent` | Email sent, no reply yet |
| `replied` | Lead replied (manual update) |
| `interested` | Lead expressed interest (manual update) |
| `unsubscribed` | Lead asked to be removed |
| `bounced` | Email bounced |

`sent` is set automatically by the agent. Other statuses are updated manually or by a future response-monitoring feature.

---

## 8. Module Architecture

### 8.1 Data Flow Diagram

```
+------------------+     +------------------+     +-------------------+
|  Google Sheet    | --> | outreach_sheets  | --> |  LangGraph State  |
| (uncontacted     |     | .load_uncontacted|     |  (leads list)     |
|  leads)          |     |  _leads()        |     |                   |
+------------------+     +------------------+     +--------+----------+
                                                           |
                                                           v
                                                  +--------+----------+
                                                  | readme_fetcher    |
                                                  | .fetch_readme()   |
                                                  | (GitHub API)      |
                                                  +--------+----------+
                                                           |
                                                           v
                                                  +--------+----------+
                                                  | email_generator   |
                                                  | .generate_email() |
                                                  | (Claude API)      |
                                                  +--------+----------+
                                                           |
                                                           v
                                                  +--------+----------+
                                                  | CLI Review        |
                                                  | (human approval)  |
                                                  +--------+----------+
                                                           |
                                                           v
                                                  +--------+----------+
                                                  | email_sender      |
                                                  | .send_email()     |
                                                  | (Outlook SMTP)    |
                                                  +--------+----------+
                                                           |
                                                           v
                                                  +--------+----------+
                                                  | outreach_sheets   |
                                                  | .mark_contacted() |
                                                  | (Sheet writeback) |
                                                  +--------+----------+
```

### 8.2 Module Definitions

#### `outreach_config.py`
- **Purpose**: Outreach-specific configuration constants and env var loading
- **Inputs**: Environment variables, .env file
- **Outputs**: Config constants (SMTP settings, Claude API key, batch size, pacing params)

#### `outreach_state.py`
- **Purpose**: LangGraph state schema definition
- **Inputs**: None (type definitions only)
- **Outputs**: `OutreachState` TypedDict

#### `outreach_sheets.py`
- **Purpose**: Google Sheets read/write functions specific to outreach
- **Inputs**: Worksheet object, row data
- **Outputs**: Lead dicts, updated rows
- **Key functions**: `load_uncontacted_leads()`, `mark_lead_contacted()`, `mark_lead_bounced()`
- **Reuses**: `sheets.py` for `connect_to_sheet()`, `_retry_write()`

#### `readme_fetcher.py`
- **Purpose**: Fetch and truncate GitHub repo READMEs
- **Inputs**: repo_url or repo full_name
- **Outputs**: README text (truncated to 2000 chars) or empty string
- **Reuses**: `github_client.py` — add a `get_readme()` method to `GitHubClient`

#### `email_generator.py`
- **Purpose**: Generate personalized emails via Claude API
- **Inputs**: Lead dict + README text
- **Outputs**: Dict with `subject` and `body` keys
- **Dependencies**: `anthropic` Python SDK, `CHOX_CONTEXT.md` (loaded once at init)
- **Note**: Personalization comes from the repo README content, not from pain point categories

#### `email_sender.py`
- **Purpose**: Send emails via Outlook.com SMTP with pacing
- **Inputs**: Recipient email, subject, body, sender config
- **Outputs**: Success/failure status per email
- **Handles**: STARTTLS, authentication, MIME construction, send pacing, error handling

#### `outreach_graph.py`
- **Purpose**: LangGraph graph definition — nodes, edges, checkpointer
- **Inputs**: OutreachState
- **Outputs**: Compiled graph
- **Contains**: All node functions, conditional edge logic, interrupt configuration

#### `review_cli.py`
- **Purpose**: Terminal UI for human review of email batches
- **Inputs**: List of generated emails with lead context
- **Outputs**: List of approval decisions
- **Handles**: Display formatting, user input, editor integration for edits

#### `run_outreach.py`
- **Purpose**: Main entry point — `python run_outreach.py`
- **Inputs**: CLI args (optional: --resume, --dry-run, --batch-size)
- **Outputs**: Run summary
- **Reuses**: `config.py` for GITHUB_TOKEN, SPREADSHEET_ID, SERVICE_ACCOUNT_FILE

### 8.3 Reuse from Existing Codebase

| Existing File | What to Reuse |
|--------------|---------------|
| `shared/config.py` | GITHUB_TOKEN, GITHUB_HEADERS, GITHUB_API_BASE, SPREADSHEET_ID, SERVICE_ACCOUNT_FILE, RATE_LIMIT_SLEEP_CORE |
| `shared/sheets.py` | `connect_to_sheet()`, `_retry_write()`, `_ensure_headers()` |
| `shared/models.py` | `Lead` dataclass (for type reference) |
| `discovery/github_client.py` | `GitHubClient` class — extend with `get_readme()` method |
| `docs/CHOX_CONTEXT.md` | Product context loaded into Claude system prompt at runtime |
| `run.py` | Pattern to follow for `run_outreach.py` structure |

---

## 9. State Schema

```python
from typing import TypedDict, Literal


class EmailDraft(TypedDict):
    lead_index: int                    # Index into the leads list
    to_email: str
    to_name: str
    subject: str
    body: str
    lead_context: dict                 # Full lead row data for review display
    readme_snippet: str                # First 500 chars of README for review
    status: Literal["pending", "approved", "rejected", "edited", "sent", "failed", "bounced"]
    edited_body: str                   # Non-empty if human edited the email
    send_error: str                    # Error message if send failed


class OutreachState(TypedDict):
    # Input data
    leads: list[dict]                  # Lead rows from Google Sheet
    batch_index: int                   # Current batch number (0-indexed)

    # README fetch results
    readmes: dict[str, str]            # repo_full_name -> README text

    # Generated emails
    drafts: list[EmailDraft]           # One per lead in current batch

    # Human review results
    approval_decisions: list[dict]     # [{index, action, edited_body}]

    # Send results
    sent_count: int
    failed_count: int
    bounced_count: int

    # Run metadata
    daily_send_count: int              # Tracks total sent today (across batches)
    run_date: str                      # ISO date string
    errors: list[str]                  # Accumulated error messages
```

---

## 10. Configuration

### 10.1 New Environment Variables

Add to `.env`:

```bash
# Outreach agent - Email sending
SMTP_USERNAME=your-outlook-email@outlook.com
SMTP_PASSWORD=your-app-password-here

# Outreach agent - Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Outreach agent - Sender identity
SENDER_NAME=Fayzan and Dilraj, Co-founders of Chox
SENDER_EMAIL=your-outlook-email@outlook.com
PHYSICAL_ADDRESS=Chox, Inc. | [Your address here]
```

### 10.2 New Constants in `outreach_config.py`

```python
# SMTP
SMTP_HOST = "smtp-mail.outlook.com"
SMTP_PORT = 587

# Send pacing
BATCH_SIZE = 10
MIN_SEND_DELAY_SECONDS = 90
MAX_SEND_DELAY_SECONDS = 180
MAX_EMAILS_PER_DAY = 20            # Adjust during warm-up
MAX_EMAILS_PER_30_MIN = 5

# Claude API
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 1024
CLAUDE_TEMPERATURE = 0.7            # Some creativity for personalization

# README
README_MAX_CHARS = 2000             # Truncate READMEs to this length

# Checkpoint
CHECKPOINT_DB = "ghostline_outreach.db"
```

---

## 11. Dependencies

### 11.1 New Packages

Add to `requirements.txt`:

```
# Existing
requests>=2.31.0
gspread>=6.0.0
python-dotenv>=1.0.0

# New for outreach agent
langgraph>=0.2.0
langchain-core>=0.3.0
anthropic>=0.40.0
```

### 11.2 Standard Library (No Install Needed)

- `smtplib` — SMTP email sending
- `email.mime.text` — MIME message construction
- `sqlite3` — LangGraph checkpoint storage (used by SqliteSaver)
- `subprocess` — Opening $EDITOR for email edits
- `tempfile` — Temp file for editor-based email editing
- `random` — Send delay randomization

---

## 12. Daily Run Sequence

```
$ python run_outreach.py [--dry-run] [--batch-size 10] [--resume]

STEP 1: INITIALIZE
  - Load outreach config (SMTP creds, API keys, send limits)
  - Connect to Google Sheet (reuse sheets.py)
  - Initialize GitHubClient (reuse github_client.py)
  - Initialize Claude client (anthropic SDK)
  - Set up LangGraph checkpointer (SqliteSaver)
  - Check daily send count from checkpoint DB (if resuming)

STEP 2: LOAD LEADS
  - Read all rows from sheet via get_all_records()
  - Filter: contacted == "FALSE", email non-empty, response_status != "unsubscribed"
  - Sort by lead_score descending (highest value leads first)
  - Slice to BATCH_SIZE (default 10)
  - If no leads: print "No uncontacted leads available" and exit

STEP 3: FETCH READMES
  - For each lead, extract repo full_name from repo_url
  - Call GitHub API: GET /repos/{owner}/{repo}/readme (Accept: application/vnd.github.raw)
  - Truncate to README_MAX_CHARS (2000 chars)
  - If 404: set readme to "" (email_generator handles missing README gracefully)
  - Sleep RATE_LIMIT_SLEEP_CORE between calls

STEP 4: GENERATE EMAILS
  - For each lead + readme pair, call Claude API
  - System prompt: product context + email constraints
  - User prompt: lead name, repo name/description, README summary, frameworks
  - Parse response into {subject, body}
  - Validate: subject length <= 80 chars, body word count <= 200
  - Store as EmailDraft in state

STEP 5: HUMAN REVIEW (interrupt)
  - Display batch summary: "Generated 10 emails. Starting review..."
  - For each draft, display lead context + full email
  - Collect approval decisions (approve/reject/edit)
  - If all rejected: update notes in sheet ("rejected_in_review"), exit
  - If quit: checkpoint state, exit (resume later with --resume)

STEP 6: SEND EMAILS
  - Check daily_send_count against MAX_EMAILS_PER_DAY
  - Establish SMTP connection (STARTTLS, authenticate)
  - For each approved email:
    - Construct MIME plain text message
    - Set From, To, Subject, Reply-To headers
    - Send via SMTP
    - On success: mark draft status = "sent", increment counts
    - On failure: mark draft status = "failed", log error
    - Sleep random(MIN_SEND_DELAY, MAX_SEND_DELAY) between sends
  - Close SMTP connection

STEP 7: UPDATE SHEET
  - For each sent email: mark_lead_contacted(worksheet, row_number)
  - For each failed email: update notes with error
  - For each rejected email: update notes with "rejected_in_review"
  - Batch update via worksheet.batch_update()

STEP 8: REPORT
  - Print summary: sent/failed/rejected/bounced counts
  - Print daily total (cumulative across batches)
```

---

## 13. Error Handling & Edge Cases

### 13.1 README Not Found
GitHub API returns 404 for repos without a README. Set readme to empty string. Claude generates a less specific but still personalized email based on repo name, description, and frameworks.

### 13.2 Email Send Failure
Catch `smtplib.SMTPException`, log the error, mark draft as "failed", continue to next email. Do NOT retry immediately — a failed send may indicate a deliverability problem.

### 13.3 API Rate Limits
- **GitHub**: Reuse existing `GitHubClient` rate limit handling. README fetches use the core API pool (5000/hr).
- **Claude**: Catch `anthropic.RateLimitError`. Retry with exponential backoff (2s, 4s, 8s), max 3 retries.
- **Google Sheets**: Reuse existing `_retry_write()` with 429 backoff.

### 13.4 Empty Batches
If `load_leads` returns 0 uncontacted leads: print "No uncontacted leads available. Run Phase 1 (run.py) to discover new leads." and exit gracefully.

### 13.5 Claude Returns Malformed Email
If Claude's response doesn't contain both a subject and body: log a warning, mark draft as "failed" with note "malformed_generation", skip in review.

### 13.6 SMTP Connection Drops Mid-Batch
Mark remaining unsent emails as "failed". Proceed to update_sheet for emails that were successfully sent.

### 13.7 Daily Limit Reached Mid-Batch
Stop sending, mark remaining approved emails as "pending", print "Daily send limit reached", checkpoint state for resume.

### 13.8 Duplicate Prevention
Before sending, re-check the lead's `contacted` field (may have been updated by a concurrent run or manual edit).

---

## 14. Risks & Mitigations

### 14.1 Deliverability Risk
**Risk**: Outlook.com flags the account as spam due to cold outreach patterns.
**Mitigations**: Conservative volumes (never exceed 20/day), randomized delays, high personalization, plain text only, warm-up schedule, monitor bounce rates (abort if > 5%).

### 14.2 API Cost Risk
**Risk**: Claude API costs accumulate with high lead volumes.
**Mitigations**: Use claude-sonnet (cheaper than Opus), ~10 calls per batch at ~500 tokens each = ~$0.05-0.10 per batch. README truncation to 2,000 chars limits input tokens.

### 14.3 Outlook.com Account Suspension
**Risk**: Microsoft suspends the account for sending too many emails.
**Mitigations**: Stay well under 300/day limit, never send to bounced addresses twice, include unsubscribe in every email. If suspended: wait 24-48 hours, reduce volume, consider Microsoft 365 ($6/month) for higher limits.

### 14.4 Low Response Rates
**Risk**: Cold outreach to developers may yield < 2% response rates.
**Mitigations**: High personalization (README-based), targeted audience (building exactly what Chox helps with), low-friction CTA, follow-up sequence (future Phase 3).

### 14.5 Stale Lead Data
**Risk**: Leads discovered weeks ago may have changed projects.
**Mitigations**: Sort by lead_score descending, re-fetch README at outreach time (confirms project exists), handle bounces gracefully, prefer recently discovered leads.
