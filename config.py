"""
config.py — All constants, blocklists, keyword lists, scoring weights,
thresholds, and environment variable references for the Ghostline lead gen tool.
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")

# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------

SINCE_DATE = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
RUN_ID = date.today().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ---------------------------------------------------------------------------
# Pagination / run limits
# ---------------------------------------------------------------------------

PAGES_PER_QUERY = 3
PER_PAGE = 100
MAX_LEADS_PER_RUN = 500

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------

TIER1_THRESHOLD = 20
TIER2_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Rate limit sleep intervals (seconds)
# ---------------------------------------------------------------------------

RATE_LIMIT_SLEEP_SEARCH = 2.5
RATE_LIMIT_SLEEP_CODE_SEARCH = 7.0
RATE_LIMIT_SLEEP_CORE = 0.1
CORE_BUDGET_ABORT_THRESHOLD = 500

# ---------------------------------------------------------------------------
# Search queries
# ---------------------------------------------------------------------------

SEARCH_QUERIES = [
    f"langchain language:python pushed:>{SINCE_DATE} fork:false",
    f"langgraph language:python pushed:>{SINCE_DATE} fork:false",
    f"langchain language:typescript pushed:>{SINCE_DATE} fork:false",
    f"langgraph language:typescript pushed:>{SINCE_DATE} fork:false",
    f"langchain+agent pushed:>{SINCE_DATE} fork:false",
    f"langgraph+agent pushed:>{SINCE_DATE} fork:false",
]

# ---------------------------------------------------------------------------
# Import signal tiers
# ---------------------------------------------------------------------------

TIER_A_IMPORTS = [
    "from langchain.tools import tool",
    "from langchain.tools import Tool",
    "from langchain.tools import StructuredTool",
    "from langchain_core.tools import tool",
    "from langchain_core.tools import BaseTool",
    "from langchain_community.tools import",
    "from langgraph.prebuilt import ToolNode",
    "from langgraph.prebuilt import tools_condition",
    "from langchain.agents import create_tool_calling_agent",
    "from langchain.agents import AgentExecutor",
    "from langchain.agents import create_react_agent",
    "from langchain.agents import create_openai_tools_agent",
    "from crewai import Agent",
    "from crewai.tools import tool",
    "from autogen import AssistantAgent",
]

TIER_B_IMPORTS = [
    "from langgraph.graph import StateGraph",
    "from langgraph.graph import MessageGraph",
    "from langgraph.graph import END",
    "from langgraph.checkpoint import MemorySaver",
    "from langgraph.prebuilt import create_react_agent",
    "from langchain.chains import LLMChain",
]

TIER_C_IMPORTS = [
    "from langchain_community.tools.gmail import",
    "from langchain_community.tools.slack import",
    "from langchain_community.tools.sql_database import",
    "from langchain_community.tools.file_management import",
    "from langchain_community.utilities.sql_database import SQLDatabase",
    "from langchain_experimental.sql import SQLDatabaseChain",
    "import stripe",
    "import boto3",
    "import twilio",
    "import sendgrid",
    "import plaid",
]

# ---------------------------------------------------------------------------
# Keyword lists for production-maturity scoring
# ---------------------------------------------------------------------------

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

MODERATE_KEYWORDS = [
    "workflow", "automation", "pipeline",
    "integration", "api", "database",
    "agent", "autonomous", "agentic",
    "tool calling", "function calling",
    "multi-agent", "orchestration",
    "real-time", "async", "queue",
]

# ---------------------------------------------------------------------------
# Blocklists
# ---------------------------------------------------------------------------

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

TUTORIAL_ORG_BLOCKLIST = [
    "langchain-ai",
    "hwchase17",
    "deeplearning-ai",
    "microsoft",
    "crewAIInc",
]

# ---------------------------------------------------------------------------
# Import-to-category mapping (for pain point inference)
# ---------------------------------------------------------------------------

IMPORT_TO_CATEGORY = {
    "stripe": "financial",
    "plaid": "financial",
    "square": "financial",
    "paypal": "financial",
    "braintree": "financial",
    "sqlalchemy": "database",
    "psycopg2": "database",
    "pymongo": "database",
    "boto3": "database",
    "redis": "database",
    "langchain_community.tools.sql_database": "database",
    "langchain_experimental.sql": "database",
    "SQLDatabase": "database",
    "twilio": "communication",
    "sendgrid": "communication",
    "slack_sdk": "communication",
    "langchain_community.tools.gmail": "communication",
    "langchain_community.tools.slack": "communication",
    "langchain_community.tools.file_management": "file_system",
}

# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

INVALID_EMAIL_PATTERNS = [
    r'.*@users\.noreply\.github\.com$',
    r'^\d+\+.*@users\.noreply\.github\.com$',
    r'.*@localhost$',
    r'.*@example\.com$',
    r'^noreply@',
    r'^no-reply@',
    r'^git@',
]

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# ---------------------------------------------------------------------------
# Google Sheets column headers (order must match Lead.to_row())
# ---------------------------------------------------------------------------

GOOGLE_SHEET_HEADERS = [
    "github_username", "email", "full_name", "repo_url", "repo_name",
    "repo_description", "repo_stars", "repo_language", "frameworks_detected",
    "lead_score", "lead_tier", "inferred_pain_point", "risk_apis_detected",
    "profile_bio", "profile_company", "profile_location", "profile_blog",
    "twitter_handle", "followers", "public_repos", "email_source",
    "discovered_at", "contacted", "contacted_at", "contact_method",
    "response_status", "notes", "run_id",
]
