# Chox Lead Generation Tool — Master Implementation Plan

*Automated daily pipeline to discover 50-100 qualified developer leads on GitHub who are actively building with LangChain/LangGraph, extract their public email, and export to Google Sheets.*

---

## 1. Executive Summary

**What this tool does:** A Python CLI (`python run.py`) that runs daily to find developers actively building AI agents with LangChain or LangGraph, qualify them against a multi-signal scoring framework, extract their public email addresses, and append new leads to a Google Sheet. The tool is fully automated, zero-cost, and operates within GitHub's free-tier API limits.

**Who it targets:** Developers who have committed code importing `langchain` or `langgraph` in the last 30 days into non-fork, non-tutorial repositories. These are people building AI agents with real tool access — the exact audience that needs Chox's agent governance layer.

**Why this approach:** GitHub is the only platform where you can observe what developers are actually building (not what they claim to be building). Code search for specific import patterns is the highest-fidelity signal for identifying developers who are building agents with tool use — the exact use case Chox governs. Unlike conference attendee lists or Twitter follows, a `from langchain.tools import tool` in a production repo is proof of active development.

**Expected output:** 30-80 new qualified leads per daily run (bottlenecked by email availability — roughly 30-40% of GitHub users have resolvable public emails).

**Constraints:** GitHub API free tier (5,000 req/hr authenticated), Google Sheets as database, Python only, single-command execution, zero cost.

---

## 2. ICP & Qualifying Signals

### 2.1 Who We're Targeting

The target lead is a **software developer actively building AI agents that make real API calls** — not experimenting with LLM prompts, not building chatbots, not following a tutorial. They are writing code where an LLM decides to invoke an external tool (payment API, database query, file operation, communication platform) and that invocation executes in a staging or production environment.

**Typical roles:** Backend engineer, ML/AI engineer, platform engineer, technical co-founder, solo developer shipping a product.

**What they are building (in order of value to Chox):**

1. **Autonomous agent workflows** — LangGraph state machines or LangChain agent executors where the LLM selects and invokes tools in a loop with branching logic. Highest-value: every tool invocation is an uncontrolled action.
2. **Multi-agent systems** — Supervisor/worker patterns, CrewAI crews, AutoGen groups. Multiple agents = multiplicative risk surface.
3. **RAG pipelines with write-back actions** — Retrieval-augmented generation that takes actions (updates a database, sends a notification, creates a ticket).
4. **Custom agentic pipelines** — Developers manually wiring LLM function-calling to real API calls via their own orchestration.

### 2.2 The Pain They Feel (That Chox Solves)

| Pain Point | How It Manifests | Chox Solution |
|---|---|---|
| **Blind to agent actions** | Can see LLM traces in LangSmith/Langfuse but cannot answer "what did my agent actually DO to external systems today?" | Every tool call classified by action type (read/write/delete/financial), risk-scored (0-1), logged |
| **No safe enforcement path** | Knows their agent could make a $50K Stripe charge or drop a table, but enabling blocking risks breaking production | Shadow verdicts: see what WOULD have been blocked, tune rules, flip enforcement only when confident |
| **Audit gap** | Compliance/security review asks "show me every external action your AI took last week" — they cannot | Full audit log: action type, risk score, verdict, reason, request/response metadata, timestamp |
| **Framework lock-in fear** | Worried that adding governance means coupling to yet another platform | 2 lines of SDK code (`guard.wrap()`) or a URL change (proxy mode), zero framework dependency |

### 2.3 Qualifying Signals (Hard Requirements)

A lead is qualified if they meet **ALL** of the following:

1. Has committed code to a repo that imports `langgraph` or `langchain` in the last 30 days
2. The repo is not a fork of the official LangChain/LangGraph repos
3. The repo is not a tutorial, course, or demo (see Section 3 for filter logic)
4. Their GitHub profile or commit metadata contains a resolvable public email
5. They have not been contacted before (checked against Google Sheet)

### 2.4 Detecting Pain from Public GitHub Signals

#### High-Value Import Patterns (Code Search Targets)

**Tier A — Direct tool-calling imports (strongest signal):**
```
from langchain.tools import tool
from langchain.tools import Tool
from langchain.tools import StructuredTool
from langchain_core.tools import tool
from langchain_core.tools import BaseTool
from langchain_community.tools import *
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain.agents import create_react_agent
from langchain.agents import create_openai_tools_agent
from crewai import Agent
from crewai.tools import tool
from autogen import AssistantAgent
```

**Tier B — Framework graph/orchestration imports (strong signal when combined with Tier A):**
```
from langgraph.graph import StateGraph
from langgraph.graph import MessageGraph
from langgraph.graph import END
from langgraph.checkpoint import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain.chains import LLMChain
```

**Tier C — Specific high-risk tool integrations (strongest Chox relevance):**
```
from langchain_community.tools.gmail import *
from langchain_community.tools.slack import *
from langchain_community.tools.sql_database import *
from langchain_community.tools.file_management import *
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
import stripe
import boto3
import twilio
import sendgrid
import plaid
```

#### README / Description Keywords Indicating Production Use

**Strong production signals (2 points each in scoring):**
```python
PRODUCTION_KEYWORDS = [
    "production", "deployed", "deploy", "deployment",
    "staging", "live", "ship", "shipping",
    "infrastructure", "platform", "saas", "service",
    "api key", "api keys", "credentials",
    "monitoring", "observability", "logging",
    "scale", "scaling", "load balancing",
    "kubernetes", "k8s", "docker-compose",
    "ci/cd", "github actions", "continuous",
    "enterprise", "customer", "client",
    "billing", "payment", "subscription",
    "webhook", "cron", "scheduled",
    "rate limit", "retry", "backoff",
]
```

**Moderate production signals (1 point each):**
```python
MODERATE_KEYWORDS = [
    "workflow", "automation", "pipeline",
    "integration", "api", "database",
    "agent", "autonomous", "agentic",
    "tool calling", "function calling",
    "multi-agent", "orchestration",
    "real-time", "async", "queue",
]
```

---

## 3. Lead Scoring Framework

### 3.1 Tier Definitions

| Tier | Score Range | Meaning | Action |
|---|---|---|---|
| **Tier 1 (Hot)** | 60-100 | High-confidence production agent builder with tool use | Priority outreach, personalized message |
| **Tier 2 (Warm)** | 30-59 | Likely building agents with tools, some production signals | Standard outreach, less personalization |
| **Disqualified** | 0-29 | Tutorial, toy project, no tool use evidence | Do not contact |

### 3.2 Scoring Algorithm (0-100 Points)

```python
def score_lead(lead: dict) -> int:
    """
    Inputs (lead dict keys):
        - repo_stars: int
        - commit_count_30d: int (commits by this user in last 30 days)
        - contributor_count: int
        - has_org: bool (user belongs to a GitHub org)
        - tier_a_imports: int (count of distinct Tier A imports found)
        - tier_b_imports: int (count of distinct Tier B imports found)
        - tier_c_imports: int (count of distinct Tier C imports found)
        - production_keyword_score: int (sum from keyword matching)
        - repo_structure_score: int (sum from structure pattern matching)
        - is_tutorial: bool (True if tutorial/demo filters triggered)
        - repo_age_days: int
        - has_readme: bool
        - readme_length: int (character count)
        - user_followers: int
        - profile_company: str or None
        - profile_bio: str or None
        - profile_blog: str or None
        - frameworks_detected: list[str]
    """
    if lead["is_tutorial"]:
        return 0

    score = 0

    # === TOOL USE SIGNALS (max 35 points) ===
    score += min(lead["tier_a_imports"] * 5, 15)   # Direct tool-calling code
    score += min(lead["tier_b_imports"] * 3, 9)    # Framework orchestration
    score += min(lead["tier_c_imports"] * 5, 11)   # High-risk API integrations

    # === PRODUCTION MATURITY SIGNALS (max 30 points) ===
    score += min(lead["production_keyword_score"], 10)  # README production keywords
    score += min(lead["repo_structure_score"], 12)      # Docker, CI, tests, etc.

    if lead["repo_age_days"] >= 30:
        score += 3
    if lead["repo_age_days"] >= 90:
        score += 2  # additional

    if lead["has_readme"] and lead["readme_length"] > 500:
        score += 3

    # === SOCIAL PROOF / SCALE SIGNALS (max 20 points) ===
    if lead["repo_stars"] >= 5:
        score += 2
    if lead["repo_stars"] >= 25:
        score += 3
    if lead["repo_stars"] >= 100:
        score += 3
    if lead["repo_stars"] >= 500:
        score += 2  # cap at 10

    if lead["contributor_count"] >= 2:
        score += 3
    if lead["contributor_count"] >= 5:
        score += 3
    if lead["contributor_count"] >= 10:
        score += 2  # cap at 8 from contributors

    # === DEVELOPER PROFILE SIGNALS (max 15 points) ===
    if lead["has_org"]:
        score += 5

    if lead["commit_count_30d"] >= 5:
        score += 2
    if lead["commit_count_30d"] >= 15:
        score += 3
    if lead["commit_count_30d"] >= 30:
        score += 2  # cap at 7 from commits

    if lead["user_followers"] >= 10:
        score += 1
    if lead["user_followers"] >= 50:
        score += 1
    if lead["user_followers"] >= 200:
        score += 1  # cap at 3 from followers

    return min(score, 100)
```

### 3.3 Tutorial / Demo / Toy Project Filter

A repo is marked `is_tutorial = True` (and scored 0) if **ANY** of the following conditions are met.

#### Repo Name Blocklist

If the repo name (lowercased) contains any of these substrings:

```python
REPO_NAME_BLOCKLIST = [
    "tutorial", "course", "demo", "example", "examples",
    "learn", "learning", "starter", "template", "boilerplate",
    "awesome-", "workshop", "bootcamp", "walkthrough",
    "sample", "playground", "sandbox", "experiment",
    "study", "practice", "exercise", "homework",
    "test-", "-test", "poc", "proof-of-concept",
    "hello-world", "getting-started", "quickstart",
    "cheatsheet", "cheat-sheet", "reference",
    "notebook", "notebooks", "colab",
    "lesson", "lecture", "class-",
]
```

#### Repo Description Blocklist

If the repo description (lowercased) contains any of these phrases:

```python
DESCRIPTION_BLOCKLIST = [
    "tutorial", "course", "coursework", "demo",
    "example", "learning", "starter template",
    "workshop", "bootcamp", "walkthrough",
    "sample code", "playground", "sandbox",
    "study guide", "practice", "exercise",
    "homework", "assignment", "lecture",
    "proof of concept", "poc", "toy",
    "just for fun", "experimenting",
    "following along", "code along",
    "udemy", "coursera", "edx", "udacity",
    "deeplearning.ai", "freecodecamp",
    "youtube", "blog post", "medium article",
]
```

#### Fork of Official/Tutorial Repos

Disqualify if the repo is a fork AND the parent repo owner is in:

```python
TUTORIAL_ORG_BLOCKLIST = [
    "langchain-ai",
    "hwchase17",
    "deeplearning-ai",
    "microsoft",
    "crewAIInc",
    "langchain-ai",
]
```

#### Structural Heuristic for Toy Projects

Mark as tutorial/toy if **ALL** of these are true:
- Repo has 0 stars
- Repo has 1 contributor
- Repo has fewer than 5 files
- No Dockerfile, no CI config, no tests directory

#### Additional Heuristics

- Exclude repos where the only language is Jupyter Notebook (likely tutorials)
- Exclude repos with 0 stars AND fewer than 5 commits

### 3.4 Pain Point Inference Logic

Based on detected code patterns, assign the primary pain point to drive outreach personalization:

```python
def infer_pain_point(lead: dict) -> str:
    """
    Returns one of five pain point strings. Priority order matters.
    """
    risk_apis = lead.get("risk_apis_detected", [])
    tool_categories = lead.get("tool_categories", [])
    framework = lead.get("framework", "")
    contributor_count = lead.get("contributor_count", 1)

    # 1. Financial API risk — most acute pain
    if "financial" in tool_categories or any(
        api in risk_apis for api in ["stripe", "plaid", "square", "paypal"]
    ):
        return "financial_risk"
        # Angle: "Your agent has access to payment APIs.
        # Do you know every charge it's made this week?"

    # 2. Database write/delete risk
    if "database" in tool_categories or any(
        api in risk_apis for api in ["boto3", "sqlalchemy", "psycopg2", "pymongo"]
    ):
        return "data_mutation_risk"
        # Angle: "Your agent can write to your database.
        # Can you see every query it ran yesterday?"

    # 3. Communication/external API risk
    if "communication" in tool_categories or any(
        api in risk_apis for api in ["twilio", "sendgrid", "slack_sdk"]
    ):
        return "communication_risk"
        # Angle: "Your agent sends messages on behalf of your product.
        # What happens when it sends the wrong one?"

    # 4. Multi-agent / team complexity
    if contributor_count >= 3 and framework in ["langgraph", "crewai", "autogen"]:
        return "governance_at_scale"
        # Angle: "Multiple people are building agents on your team.
        # Who's watching what those agents do in production?"

    # 5. General tool-calling without visibility
    return "blind_tool_calls"
    # Angle: "You're building agents with tool access.
    # Can you see every action they take — classified by risk?"
```

**Tool category classification map:**

```python
IMPORT_TO_CATEGORY = {
    "stripe": "financial", "plaid": "financial", "square": "financial",
    "paypal": "financial", "braintree": "financial",
    "sqlalchemy": "database", "psycopg2": "database", "pymongo": "database",
    "boto3": "database", "redis": "database",
    "langchain_community.tools.sql_database": "database",
    "langchain_experimental.sql": "database", "SQLDatabase": "database",
    "twilio": "communication", "sendgrid": "communication",
    "slack_sdk": "communication",
    "langchain_community.tools.gmail": "communication",
    "langchain_community.tools.slack": "communication",
    "langchain_community.tools.file_management": "file_system",
}
```

---

## 4. GitHub Discovery Strategy

### 4.1 Approach: Two-Phase Search (Repo Search + Code Verification)

The GitHub Code Search API (`GET /search/code`) is limited to **10 requests per minute**. The Repository Search API (`GET /search/repositories`) allows **30 requests per minute**. The optimal strategy uses repo search as primary discovery, then verifies with targeted code inspection only when needed.

### 4.2 Phase 1: Repository Discovery

**Endpoint:** `GET https://api.github.com/search/repositories`

**Query strings (rotate daily):**

```
q=langchain language:python pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
q=langgraph language:python pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
q=langchain language:typescript pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
q=langgraph language:typescript pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
q=langchain+agent pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
q=langgraph+agent pushed:>{SINCE_DATE} fork:false&sort=updated&order=desc&per_page=100
```

Where `SINCE_DATE` = today minus 30 days in `YYYY-MM-DD` format.

**Key parameters:**
- `pushed:>YYYY-MM-DD` — filters to repos with commits in the last 30 days
- `fork:false` — excludes forked repositories at the API level
- `language:python` — limits to Python repos (primary target)
- `sort=updated&order=desc` — most recently active first
- `per_page=100` — maximum results per page
- `page=1` through `page=10` — pagination (max 1000 results per query)

**Pagination:** Each query returns max 1000 results (10 pages of 100). The `total_count` field tells total matches. Paginate up to 3 pages per query to conserve budget.

### 4.3 Phase 2: Code Verification (Targeted)

For repos where the name/description/topics don't already contain clear langchain/langgraph signals, verify actual imports via code search.

**Endpoint:** `GET https://api.github.com/search/code`

```
q="from langchain" repo:{owner}/{repo}&per_page=1
q="from langgraph" repo:{owner}/{repo}&per_page=1
q="import langchain" repo:{owner}/{repo}&per_page=1
q="import langgraph" repo:{owner}/{repo}&per_page=1
```

**Optimization:** Skip code verification for repos that have "langchain" or "langgraph" in their `description`, `topics` array, or repo name. The repo search already matched on these terms.

### 4.4 Fork Detection and Exclusion

1. `fork:false` in search query excludes forks at the API level
2. Double-check `repo['fork'] == False` in response objects
3. Exclude repos where `owner.login` is in `TUTORIAL_ORG_BLOCKLIST`

### 4.5 Rate Limit Budget for Discovery

| Step | Calls | Rate Pool |
|------|-------|-----------|
| 6 repo search queries x 3 pages each | 18 | Search: 30/min |
| Code verification for ~50% of candidates | 50-150 | Code search: 10/min |
| **Total discovery** | **~70-170 calls** | **~16 min wall time** |

---

## 5. Email Extraction Strategy

### 5.1 Fallback Chain (Execute in Order, Stop on First Valid Email)

#### Method 1: GitHub User Profile API
**Endpoint:** `GET https://api.github.com/users/{username}`

Check the `email` field. Returns `null` if no public email is set.

- Cost: 1 API call per user
- Success rate: ~15-20% of GitHub users

#### Method 2: Commit Metadata
**Endpoint:** `GET https://api.github.com/repos/{owner}/{repo}/commits?author={username}&per_page=5`

Parse `commit.author.email` and `commit.committer.email`. These come from the user's local git config and are often real addresses even when profile email is private.

- Cost: 1 API call per user
- Success rate: ~60-70%

#### Method 3: Public Events API
**Endpoint:** `GET https://api.github.com/users/{username}/events/public?per_page=100`

Look for `PushEvent` types. Each push event contains `payload.commits[]` with `author.email`.

- Cost: 1 API call per user
- Success rate: ~50-60%

#### Method 4: Bio Parsing
From the Method 1 response, regex-parse the `bio` field for email patterns.

```python
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
```

- Cost: 0 additional API calls (reuse Method 1 response)

### 5.2 Email Validation Rules

**Discard these emails:**

```python
INVALID_EMAIL_PATTERNS = [
    r'.*@users\.noreply\.github\.com$',       # GitHub noreply (old: USERNAME@)
    r'^\d+\+.*@users\.noreply\.github\.com$', # GitHub noreply (new: ID+USERNAME@)
    r'.*@localhost$',
    r'.*@example\.com$',
    r'^noreply@',
    r'^no-reply@',
    r'^git@',
]
```

**If multiple valid emails found, prefer in order:**
1. Email from GitHub profile (user explicitly chose to make it public)
2. Most frequently occurring email across commits
3. Non-gmail/non-freemail addresses (more likely professional)

### 5.3 Email Extraction Budget

| Scenario | Calls per User | For 100 Users |
|----------|---------------|---------------|
| Email found in profile (Method 1) | 1 | 100 |
| Email found in commits (Methods 1+2) | 2 | 200 |
| Full fallback chain (Methods 1-3) | 3 | 300 |

Against the 5000/hr core rate limit, this is trivial.

---

## 6. Lead Database Schema

### 6.1 Google Sheets Column Structure

| Column | Header | Type | Purpose |
|--------|--------|------|---------|
| A | `github_username` | String | **Primary unique key.** Used for deduplication |
| B | `email` | String | Resolved public email address |
| C | `full_name` | String | Name from GitHub profile |
| D | `repo_url` | String | URL of the qualifying repo |
| E | `repo_name` | String | `full_name` field of the repo (owner/name) |
| F | `repo_description` | String | Repo description (truncated to 200 chars) |
| G | `repo_stars` | Integer | Star count at time of discovery |
| H | `repo_language` | String | Primary language |
| I | `frameworks_detected` | String | Comma-separated: "langchain", "langgraph", etc. |
| J | `lead_score` | Integer | Calculated score 0-100 |
| K | `lead_tier` | String | "tier_1", "tier_2" |
| L | `inferred_pain_point` | String | "financial_risk", "data_mutation_risk", etc. |
| M | `risk_apis_detected` | String | Comma-separated: "stripe", "boto3", etc. |
| N | `profile_bio` | String | GitHub bio (truncated to 200 chars) |
| O | `profile_company` | String | Company field |
| P | `profile_location` | String | Location field |
| Q | `profile_blog` | String | Blog/website URL |
| R | `twitter_handle` | String | Twitter username |
| S | `followers` | Integer | GitHub follower count |
| T | `public_repos` | Integer | Number of public repos |
| U | `email_source` | String | "profile", "commits", "events", "bio" |
| V | `discovered_at` | ISO 8601 | When this lead was first added |
| W | `contacted` | String | "FALSE" (default) or "TRUE" |
| X | `contacted_at` | ISO 8601 | When outreach was sent (blank until contacted) |
| Y | `contact_method` | String | "email", "twitter", etc. (blank until contacted) |
| Z | `response_status` | String | "none", "replied", "interested", "not_interested", "bounced" |
| AA | `notes` | String | Free-form notes |
| AB | `run_id` | String | ISO date of the run (e.g., "2026-03-17") |

### 6.2 Deduplication Logic

- **Unique key:** Column A (`github_username`)
- At startup, load all values: `existing_users = set(worksheet.col_values(1))`
- Before inserting, check `if username in existing_users: skip`
- O(1) lookup via Python set

### 6.3 Contacted Status Tracking

- `contacted` column defaults to `"FALSE"` on insert
- Outreach team manually sets to `"TRUE"` and fills `contacted_at`, `contact_method`
- The tool checks `contacted` column is NOT used for dedup — only `github_username` uniqueness matters
- `response_status` defaults to `"none"` and is manually updated

### 6.4 Google Sheets Authentication

**Library:** `gspread` (Python package, uses service account)

```python
import gspread
gc = gspread.service_account(filename='service_account.json')
sheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = sheet.sheet1
```

---

## 7. Tool Architecture

### 7.1 ASCII Pipeline Diagram

```
run.py (entry point)
  |
  v
+-------------------+     +-------------------+     +--------------------+
| discover.py       | --> | qualify.py        | --> | extract_email.py   |
| - Search GitHub   |     | - Filter forks    |     | - Profile email    |
|   repos via API   |     | - Filter tutorials|     | - Commit email     |
| - Paginate results|     | - Filter official |     | - Events email     |
| - Return raw list |     |   repos           |     | - Bio parsing      |
+-------------------+     | - Verify imports  |     | - Validate email   |
                          +-------------------+     +--------------------+
                                                           |
                                                           v
                                                    +--------------------+
                                                    | score.py           |
                                                    | - Score leads 0-100|
                                                    | - Assign tier      |
                                                    | - Infer pain point |
                                                    +--------------------+
                                                           |
                                                           v
                                                    +--------------------+
                                                    | sheets.py          |
                                                    | - Dedup check      |
                                                    | - Insert new leads |
                                                    +--------------------+
                                                           |
                                                           v
                                                    +--------------------+
                                                    | report.py          |
                                                    | - Print summary    |
                                                    | - Log run stats    |
                                                    +--------------------+

Supporting modules:
+-------------------+     +-------------------+     +--------------------+
| github_client.py  |     | config.py         |     | models.py          |
| - Auth setup      |     | - Load .env       |     | - Lead dataclass   |
| - Rate limiter    |     | - Constants       |     | - Repo dataclass   |
| - Request wrapper |     | - Query templates |     |                    |
+-------------------+     | - Blocklists      |     +--------------------+
                          +-------------------+
```

### 7.2 Data Flow

```
Search Queries --> [discover.py] --> Raw Repos (200-500)
                                          |
                                          v
                                   [qualify.py] --> Qualified Repos (80-200)
                                                         |
                                                         v
                                               [extract_email.py] --> Leads with Emails (50-100)
                                                                           |
                                                                           v
                                                                    [score.py] --> Scored & Tiered Leads
                                                                                        |
                                                                                        v
                                                                                 [sheets.py] --> New Leads Added (30-80)
                                                                                                      |
                                                                                                      v
                                                                                                [report.py] --> Summary
```

---

## 8. Module Specifications

### 8.1 `run.py` — Entry Point

**Purpose:** Orchestrate the full pipeline in sequence.

**Inputs:** None (reads config from `.env`)

**Outputs:** Exit code 0 on success, 1 on failure. Prints summary to stdout.

**Logic:**
1. Load config
2. Initialize GitHub client
3. Connect to Google Sheets, load existing usernames
4. Run discovery -> qualification -> email extraction -> scoring -> sheets insert
5. Print report
6. Catch all exceptions, log, exit cleanly

### 8.2 `config.py` — Configuration

**Purpose:** Central configuration, constants, and blocklists.

**Inputs:** `.env` file via `python-dotenv`

**Outputs:** Exports `GITHUB_TOKEN`, `SPREADSHEET_ID`, `SERVICE_ACCOUNT_FILE`, `SINCE_DATE`, `RUN_ID`, search queries, all blocklists, keyword lists, and scoring constants.

**Logic:**
- `SINCE_DATE = (today - 30 days).strftime('%Y-%m-%d')`
- `RUN_ID = today.strftime('%Y-%m-%d')`
- All blocklists from Sections 3.3 and 2.4
- All scoring constants and thresholds

### 8.3 `github_client.py` — GitHub API Wrapper

**Purpose:** Authenticated HTTP client with rate limit management.

**Inputs:** `GITHUB_TOKEN` from config

**Outputs:** Methods that return parsed JSON responses.

**Methods:**
- `search_repos(query: str, page: int) -> dict` — calls `GET /search/repositories`
- `search_code(query: str) -> dict` — calls `GET /search/code`
- `get_user(username: str) -> dict` — calls `GET /users/{username}`
- `get_commits(owner: str, repo: str, author: str) -> list` — calls `GET /repos/{owner}/{repo}/commits`
- `get_user_events(username: str) -> list` — calls `GET /users/{username}/events/public`
- `check_rate_limit() -> dict` — calls `GET /rate_limit` (free, does not count)

**Rate limit logic:**
- Read `X-RateLimit-Remaining` and `X-RateLimit-Reset` from every response
- If remaining <= 2: sleep until reset time + 1 second
- On HTTP 403: read `Retry-After` header, sleep, retry
- On HTTP 429: sleep 60 seconds, retry
- Between search API calls: sleep 2.5 seconds
- Between code search calls: sleep 7 seconds
- Between core API calls: sleep 0.1 seconds
- If core budget drops below 500: abort run gracefully, save progress

**Headers for all requests:**
```python
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
```

### 8.4 `models.py` — Data Models

**Purpose:** Dataclasses for type safety and serialization.

```python
@dataclass
class Lead:
    github_username: str
    email: str
    full_name: str
    repo_url: str
    repo_name: str
    repo_description: str
    repo_stars: int
    repo_language: str
    frameworks_detected: str     # comma-separated
    lead_score: int
    lead_tier: str               # "tier_1" or "tier_2"
    inferred_pain_point: str     # "financial_risk", etc.
    risk_apis_detected: str      # comma-separated
    profile_bio: str
    profile_company: str
    profile_location: str
    profile_blog: str
    twitter_handle: str
    followers: int
    public_repos: int
    email_source: str            # "profile", "commits", "events", "bio"
    discovered_at: str           # ISO 8601
    contacted: str               # "FALSE"
    contacted_at: str            # ""
    contact_method: str          # ""
    response_status: str         # "none"
    notes: str                   # ""
    run_id: str                  # "2026-03-17"

    def to_row(self) -> list:
        """Convert to list for Google Sheets append."""
        return [
            self.github_username, self.email, self.full_name,
            self.repo_url, self.repo_name, self.repo_description,
            self.repo_stars, self.repo_language, self.frameworks_detected,
            self.lead_score, self.lead_tier, self.inferred_pain_point,
            self.risk_apis_detected, self.profile_bio, self.profile_company,
            self.profile_location, self.profile_blog, self.twitter_handle,
            self.followers, self.public_repos, self.email_source,
            self.discovered_at, self.contacted, self.contacted_at,
            self.contact_method, self.response_status, self.notes,
            self.run_id,
        ]
```

### 8.5 `discover.py` — Repository Discovery

**Purpose:** Search GitHub for repos matching langchain/langgraph queries.

**Inputs:** Search queries from config, `SINCE_DATE`

**Outputs:** List of raw repo dicts (deduplicated by `full_name`)

**Logic:**
1. For each query in `SEARCH_QUERIES`:
   - Call `github_client.search_repos(query, page)` for pages 1-3
   - Collect all `items` from responses
2. Deduplicate by `repo['full_name']` (use a dict keyed on full_name)
3. Return list of unique repo dicts

**Edge cases:**
- Some queries may return 0 results (fine, skip)
- `total_count` may exceed 1000 but API only returns first 1000
- Empty `items` array means no more results for that query

### 8.6 `qualify.py` — Lead Qualification

**Purpose:** Filter repos to only those that are legitimate, non-tutorial projects.

**Inputs:** List of raw repo dicts

**Outputs:** List of qualified repo dicts

**Logic (filter in order):**
1. `repo['fork'] == False` — double-check API filter
2. `repo['owner']['login']` not in `TUTORIAL_ORG_BLOCKLIST`
3. Repo name does not match any `REPO_NAME_BLOCKLIST` pattern
4. Repo description does not match any `DESCRIPTION_BLOCKLIST` pattern
5. Not Jupyter-notebook-only (check `language != "Jupyter Notebook"` or has other languages)
6. Passes structural heuristic (not 0 stars + <5 commits for solo repos)
7. Optional: code search verification for borderline cases where repo metadata doesn't clearly mention langchain/langgraph

### 8.7 `extract_email.py` — Email Extraction & Profile Enrichment

**Purpose:** For each qualifying repo owner, attempt to find a public email and enrich with profile data.

**Inputs:** List of qualified repo dicts, set of existing usernames (for dedup)

**Outputs:** List of `Lead` objects (only those with valid emails)

**Logic:**
1. Collect unique usernames from `repo['owner']['login']`
2. Remove usernames already in `existing_users` set
3. For each username:
   a. Call `get_user(username)` — check `email` field
   b. If no email: call `get_commits(owner, repo, username)` — parse `commit.author.email`
   c. If no email: call `get_user_events(username)` — parse PushEvent commit emails
   d. Parse `bio` for email regex
   e. Validate all found emails against `INVALID_EMAIL_PATTERNS`
   f. If valid email found: build partial Lead object with profile data
4. Return list of leads with valid emails

### 8.8 `score.py` — Lead Scoring & Pain Point Inference

**Purpose:** Score each lead and assign tier + pain point.

**Inputs:** List of Lead objects (partially filled from extract_email)

**Outputs:** List of Lead objects with `lead_score`, `lead_tier`, `inferred_pain_point` filled

**Logic:**
1. For each lead:
   a. Determine `tier_a_imports`, `tier_b_imports`, `tier_c_imports` counts (from code search results or repo metadata)
   b. Calculate `production_keyword_score` from repo description/README keywords
   c. Calculate `repo_structure_score` (Dockerfile, CI, tests presence — may require additional API calls or skip for simplicity)
   d. Run `score_lead()` function
   e. Assign `lead_tier` based on score ranges
   f. Run `infer_pain_point()` function
2. Filter out disqualified leads (score < 30)
3. Return scored leads

**Implementation note:** Full repo structure analysis (checking file tree for Dockerfile, CI, tests) costs 1 API call per repo. To conserve budget, only do this for repos that score >= 20 from other signals. For repos where metadata alone gives a high score, skip structure check.

### 8.9 `sheets.py` — Google Sheets Integration

**Purpose:** Connect to Google Sheets, handle dedup, insert new leads.

**Inputs:** List of `Lead` objects

**Outputs:** Count of new leads added

**Logic:**
1. Connect via `gspread.service_account(filename=SERVICE_ACCOUNT_FILE)`
2. Open sheet by key: `gc.open_by_key(SPREADSHEET_ID).sheet1`
3. Load existing usernames: `existing_users = set(worksheet.col_values(1))`
4. Filter leads: remove any where `lead.github_username in existing_users`
5. Convert remaining leads to rows via `lead.to_row()`
6. Batch append: `worksheet.append_rows(rows, value_input_option='USER_ENTERED')`
7. Return count

### 8.10 `report.py` — Run Summary

**Purpose:** Print formatted summary and log run stats.

**Inputs:** Run statistics dict

**Outputs:** Prints to stdout, appends to `runs.log`

**Logic:**
```
=== Ghostline Run Report ({RUN_ID}) ===
Repos discovered:      {X}
Repos qualified:       {Y}
Users processed:       {Z}
Emails found:          {W}
  - Tier 1 leads:      {T1}
  - Tier 2 leads:      {T2}
New leads added:       {V}
Already in sheet:      {S}
API calls used:        {A}
Run duration:          {T}s
========================================
```

---

## 9. Setup Requirements

### 9.1 Python Dependencies

**`requirements.txt`:**
```
requests>=2.31.0
gspread>=6.0.0
python-dotenv>=1.0.0
```

Three dependencies. Intentionally minimal.

### 9.2 Environment Variables

**`.env` file:**
```bash
# GitHub Personal Access Token (classic)
# Generate at: https://github.com/settings/tokens
# Scopes: NONE needed (public data only, but auth raises rate limit to 5000/hr)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Google Sheets spreadsheet ID
# From the URL: https://docs.google.com/spreadsheets/d/{THIS_PART}/edit
SPREADSHEET_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ

# Path to Google service account JSON key file
SERVICE_ACCOUNT_FILE=service_account.json
```

### 9.3 GitHub Personal Access Token Setup

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "ghostline-discovery"
4. Expiration: 90 days (set calendar reminder to renew)
5. Scopes: **No scopes needed** (public data only — auth raises rate limit from 60/hr to 5000/hr)
6. Copy token into `.env`

### 9.4 Google Cloud Project Setup

1. Go to https://console.cloud.google.com/
2. Create new project: "ghostline-leads"
3. APIs & Services > Library > enable **Google Sheets API**
4. APIs & Services > Library > enable **Google Drive API**
5. APIs & Services > Credentials > Create Credentials > Service Account
6. Name: "ghostline-bot", click Done
7. Click into the service account > Keys tab > Add Key > JSON
8. Download, rename to `service_account.json`, place in project root
9. Create a Google Sheet at sheets.google.com, name it "Ghostline Leads"
10. Add header row with all column names from Section 6.1
11. Share the sheet with the `client_email` from `service_account.json` (Editor access)
12. Copy the spreadsheet ID from the URL into `.env`

### 9.5 Project File Structure

```
ghostline/
  run.py
  config.py
  models.py
  github_client.py
  discover.py
  qualify.py
  extract_email.py
  score.py
  sheets.py
  report.py
  requirements.txt
  .env                    # NOT committed to git
  service_account.json    # NOT committed to git
  .gitignore
  runs.log               # Auto-generated
```

### 9.6 `.gitignore`

```
.env
service_account.json
runs.log
__pycache__/
*.pyc
```

---

## 10. Daily Run Sequence

When `python run.py` executes:

```
STEP 1: INITIALIZE
  - Load .env variables via python-dotenv
  - Initialize GitHub client with Bearer token
  - Verify GitHub auth: GET /rate_limit (if fails, exit with clear error)
  - Connect to Google Sheets via gspread service account
  - Load existing usernames from sheet column A into Python set
  - Calculate SINCE_DATE = (today - 30 days) as YYYY-MM-DD
  - Set RUN_ID = today as YYYY-MM-DD

STEP 2: DISCOVER REPOSITORIES
  - For each query in SEARCH_QUERIES (6 queries):
      - Call GET /search/repositories with query + pushed:>{SINCE_DATE} + fork:false
      - Paginate pages 1-3 (per_page=100)
      - Sleep 2.5s between requests
      - Collect all repo objects
  - Deduplicate repos by full_name
  - Log: "Discovered {N} unique repositories"

STEP 3: QUALIFY REPOSITORIES
  - For each repo:
      - Check fork == False
      - Check owner not in TUTORIAL_ORG_BLOCKLIST
      - Check name/description against blocklists
      - Apply structural heuristics
      - If borderline: code search verification (sleep 7s between calls)
  - Log: "Qualified {N} repositories from {M} candidates"

STEP 4: EXTRACT EMAILS & ENRICH PROFILES
  - Collect unique usernames from qualified repos
  - Remove usernames already in Google Sheet (dedup)
  - For each new username:
      - Try email fallback chain (Methods 1-4)
      - Sleep 0.1s between core API calls
      - If valid email found: build Lead object with profile data
  - Log: "Extracted emails for {N} of {M} users"

STEP 5: SCORE & CLASSIFY LEADS
  - For each Lead:
      - Calculate lead_score via scoring algorithm
      - Assign lead_tier ("tier_1" if >= 60, "tier_2" if >= 30)
      - Infer pain point
  - Filter out disqualified leads (score < 30)
  - Log: "Scored {N} leads: {T1} tier 1, {T2} tier 2"

STEP 6: WRITE TO GOOGLE SHEETS
  - Convert Lead objects to row arrays
  - Batch append via worksheet.append_rows()
  - Log: "Added {N} new leads to sheet"

STEP 7: REPORT
  - Print formatted summary to stdout
  - Append summary to runs.log
  - Exit code 0
```

**Expected wall time:** 15-30 minutes per run
**Expected output:** 30-80 new qualified leads per run

---

## 11. Known Risks & Mitigations

### Risk 1: GitHub Terms of Service

**The risk:** GitHub ToS Section H prohibits using the API "to download data or Content from GitHub for spamming purposes, including for the purposes of selling GitHub users' personal information."

**Mitigation:**
- Collect ONLY publicly available emails that users chose to make visible
- Outreach must be genuinely relevant (Chox solves a real problem for these developers)
- Emails are NOT sold or shared with third parties
- Volume is low (50-100 leads/day, not mass scraping)
- Each outreach must be personalized and reference their specific repo/work
- Include clear opt-out in every message
- **The tool automates discovery only, NOT email sending**
- Keep outreach under 30 emails per day

**Remaining risk:** GitHub could still interpret automated email collection as a ToS violation. The line between "lead research" and "spamming purposes" is subjective. If GitHub sends a warning, immediately cease automated collection.

### Risk 2: Code Search Rate Limit Bottleneck

**The risk:** 10 requests per minute for code search is restrictive. Verifying 200 repos = 20 minutes of code search alone.

**Mitigation:**
- Use code search only as verification, not primary discovery
- Skip verification for repos with clear langchain/langgraph signals in metadata
- Cache verified repos between runs to avoid re-checking

### Risk 3: Low Email Yield

**The risk:** Many GitHub users keep email private. Realistic expectation: 30-40% yield.

**Mitigation:**
- 4-method fallback chain maximizes extraction
- Commit metadata is most reliable (git config often not changed)
- For high-value leads without email: capture Twitter, blog, company for manual outreach
- Cast a wide net — qualify more repos than needed

### Risk 4: False Positives

**The risk:** Repos might mention "langchain" in negative context, comparison, or unrelated dependency.

**Mitigation:**
- Require actual import statements in code (not just README mentions)
- Code search verifies `"from langchain"` or `"import langchain"` in code files
- Tutorial/demo filter removes educational content
- Scoring algorithm deprioritizes low-signal repos

### Risk 5: Stale Data / Duplicate Outreach

**The risk:** Daily runs could surface the same users repeatedly.

**Mitigation:**
- Dedup against `github_username` column on every run
- `contacted` column prevents re-contacting
- `run_id` tracks which run found each lead
- `pushed:>` date filter naturally rotates results

### Risk 6: Google Sheets API Limits

**The risk:** 100 requests per 100 seconds per user.

**Mitigation:**
- Use `append_rows()` for batch inserts (1 call, not N calls)
- Load usernames in single `col_values()` call at startup
- Typical run makes fewer than 10 Sheets API calls total

### Risk 7: Token Expiration

**The risk:** GitHub PAT expires, or service account key is rotated.

**Mitigation:**
- At startup, call `GET /rate_limit` to verify GitHub auth — exit immediately with clear error if auth fails
- Set GitHub PAT to 90 days, set calendar reminder
- Google service account keys don't expire unless manually revoked

### Risk 8: Scoring Accuracy

**The risk:** Point-based scoring may over/under-weight certain signals, leading to mis-tiered leads.

**Mitigation:**
- All thresholds and weights are configurable in `config.py`
- After first 2 weeks, review tier 1 vs tier 2 response rates and adjust weights
- The scoring algorithm is intentionally transparent (no ML black box) for easy tuning

---

## Appendix A: Key API Reference

### Headers for All GitHub Requests

```python
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
```

### Endpoint Quick Reference

| Purpose | Method | URL | Rate Pool |
|---------|--------|-----|-----------|
| Search repos | GET | `https://api.github.com/search/repositories?q={query}` | Search: 30/min |
| Search code | GET | `https://api.github.com/search/code?q={query}` | Code search: 10/min |
| User profile | GET | `https://api.github.com/users/{username}` | Core: 5000/hr |
| Repo commits | GET | `https://api.github.com/repos/{owner}/{repo}/commits` | Core: 5000/hr |
| User events | GET | `https://api.github.com/users/{username}/events/public` | Core: 5000/hr |
| Rate limit | GET | `https://api.github.com/rate_limit` | Free |
| Sheets append | POST | Google Sheets API v4 | 100 req/100s |

### Response Field Paths

**Repo search result:**
```
response['items'][i]['full_name']        -> "owner/repo-name"
response['items'][i]['html_url']         -> "https://github.com/owner/repo"
response['items'][i]['description']      -> "Repo description"
response['items'][i]['fork']             -> false
response['items'][i]['stargazers_count'] -> 42
response['items'][i]['language']         -> "Python"
response['items'][i]['pushed_at']        -> "2026-03-15T10:30:00Z"
response['items'][i]['owner']['login']   -> "username"
response['items'][i]['topics']           -> ["langchain", "ai-agent"]
response['total_count']                  -> 1523
```

**User profile:**
```
response['login']              -> "username"
response['name']               -> "John Doe"
response['email']              -> "john@example.com" or null
response['bio']                -> "AI developer..."
response['company']            -> "@some-company"
response['location']           -> "San Francisco"
response['blog']               -> "https://johndoe.dev"
response['twitter_username']   -> "johndoe"
response['followers']          -> 150
response['public_repos']       -> 42
```

**Commit metadata:**
```
response[i]['commit']['author']['name']     -> "John Doe"
response[i]['commit']['author']['email']    -> "john@example.com"
response[i]['commit']['committer']['email'] -> "john@example.com"
```

---

## Appendix B: Agent Disagreement Resolution

### Discovery Approach: Repo Search vs Code Search as Primary

**Outbound Strategist preference:** Use code search as primary (search for exact import patterns like `from langchain.tools import tool`) — highest-fidelity signal, directly finds tool-calling code.

**Growth Hacker preference:** Use repo search as primary (search for "langchain" in repo metadata) with code search as verification — avoids the 10 req/min bottleneck on code search.

**Tradeoff:** Code-search-first finds higher-quality leads but can only process ~60 repos in 10 minutes. Repo-search-first processes hundreds of repos quickly but includes more noise.

**Decision: Repo search as primary, code search as verification.** The 10/min limit on code search makes it unsuitable as the primary discovery mechanism for a tool targeting 50-100 leads/day. Repo search at 30/min provides sufficient throughput. Code search is reserved for borderline cases where repo metadata is ambiguous. The tutorial/demo filter and scoring algorithm compensate for the lower initial precision.

### Scoring Complexity: Simple Formula vs Full Signal Analysis

**Outbound Strategist preference:** Rich scoring with 4 categories, 35+ signals, repo structure analysis, README keyword scanning — maximum discrimination between leads.

**Growth Hacker preference:** Simple formula (`stars + followers + company + bio + langgraph bonus`) — fast, few API calls, easy to tune.

**Tradeoff:** Rich scoring costs additional API calls per repo (tree endpoint, README endpoint, contributors endpoint) but produces better tier assignments. Simple scoring is free (uses data already fetched) but may mis-tier leads.

**Decision: Rich scoring with budget-aware execution.** Use the full scoring algorithm but only fetch repo structure data for repos that score >= 20 from metadata signals alone. This limits additional API calls to ~50-80 per run (repos that are borderline) rather than all 200+. The additional calls are well within rate limits.

---

*This document is implementation-ready. All keyword lists, scoring weights, thresholds, API endpoints, and module specifications can be directly translated to Python code by a coding agent.*

Sources:
- [GitHub REST API Search Endpoints](https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28)
- [GitHub Rate Limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [GitHub Code Search](https://docs.github.com/en/search-github/searching-on-github/searching-code)
- [GitHub Repository Search](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories)
- [GitHub Commits API](https://docs.github.com/en/rest/commits/commits)
- [GitHub Users API](https://docs.github.com/en/rest/users/users)
- [GitHub Events API](https://docs.github.com/en/rest/activity/events)
- [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- [GitHub Noreply Email Reference](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference)
- [gspread Authentication](https://docs.gspread.org/en/v6.1.2/oauth2.html)
- [LangChain Tools Documentation](https://docs.langchain.com/oss/python/langchain/tools)
- [LangGraph Repository](https://github.com/langchain-ai/langgraph)
