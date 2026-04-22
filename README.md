# Ghostline

Automated GitHub lead generation and outreach tool for [Chox](https://chox.ai). Discovers developers actively building with LangChain and LangGraph, extracts their public contact information, scores them against a multi-signal framework, exports qualified leads to Google Sheets daily, and enables personalized cold email outreach with human review before anything is sent.

## Background — What Is Chox?

Chox is an **AI agent governance layer** — infrastructure that sits between an AI agent and the external APIs it calls (Stripe, databases, Twilio, file systems, etc.). It classifies every tool call by action type and risk, evaluates it against configurable policy rules, and logs a shadow verdict. In shadow mode the verdict is recorded but the call goes through — giving developers visibility into what _would have been blocked_ before they turn enforcement on. When enforcement is enabled, a `block` verdict stops the agent from calling the underlying API entirely.

The meaningful distinction from existing tools: **LangSmith governs what the LLM says. Chox governs what the agent does.**

The ideal Chox customer is a developer using LangGraph, LangChain, CrewAI, or a similar framework to build agents that make real, consequential API calls — moving money, modifying databases, sending messages. Ghostline finds these developers on GitHub.

## Quick Start

Requires **Python 3.10+**.

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-org/ghostline.git
   cd ghostline
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in the three required values (see table below).

5. **Set up a GitHub Personal Access Token**
   - Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
   - Generate a classic token with **no scopes** selected (public data only)
   - Authentication is needed to raise the API rate limit from 60 requests/hour (unauthenticated) to 5,000 requests/hour
   - Paste the token into `GITHUB_TOKEN` in your `.env` file

6. **Set up a Google Cloud service account**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (or use an existing one)
   - Enable the **Google Sheets API** and **Google Drive API**
   - Go to **IAM & Admin > Service Accounts** and create a new service account
   - Click the service account, go to **Keys > Add Key > Create new key > JSON**
   - Download the JSON file and save it as `service_account.json` in the project root
   - Copy the service account email address (it looks like `name@project.iam.gserviceaccount.com`)

7. **Create and share a Google Sheet**
   - Create a new Google Sheet
   - Share it with the service account email address (Editor permission)
   - Copy the spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Paste the ID into `SPREADSHEET_ID` in your `.env` file

8. **Run**

   ```bash
   python run.py
   ```

## Environment Variables

| Variable               | Description                                              | Example                                        |
| ---------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| `GITHUB_TOKEN`         | GitHub Personal Access Token (classic, no scopes needed) | `ghp_xxxxxxxxxxxx`                             |
| `SPREADSHEET_ID`       | Google Sheets spreadsheet ID from the sheet URL          | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms` |
| `SERVICE_ACCOUNT_FILE` | Path to Google Cloud service account JSON key file       | `service_account.json`                         |

## How It Works

The pipeline runs in seven steps:

1. **Discover** -- Searches GitHub for repositories matching LangChain/LangGraph import patterns across six search queries, paginating up to three pages each.
2. **Qualify** -- Filters out forks, tutorials, demos, official example repos, and low-signal projects using name/description blocklists and structural heuristics.
3. **Extract emails** -- For each unique repository owner, runs a four-method email fallback chain: GitHub profile, commit metadata, public events API, and bio regex parsing.
4. **Score** -- Calculates a 0-100 lead score based on tool use signals, production maturity indicators, social proof, and developer profile signals. Assigns tier-1 (score >= 60) or tier-2 (score >= 30) classification and infers a pain point category.
5. **Write to Sheets** -- Deduplicates against existing rows and batch-appends new leads to the configured Google Sheet.
6. **Report** -- Prints a formatted run summary to stdout and appends it to `runs.log`.

## Daily Automation

Use the included shell wrapper and cron configuration to run Ghostline automatically each day.

**Manual run via wrapper:**

```bash
./scripts/run.sh
```

This activates the virtual environment, runs the pipeline, and logs output to `logs/run_YYYY-MM-DD.log`.

**Cron setup (runs daily at 6:00 AM):**

```bash
# Review the cron schedule
cat scripts/cron.txt

# Install (replaces existing crontab)
crontab scripts/cron.txt

# Or merge into existing crontab
crontab -l > /tmp/existing_cron
cat scripts/cron.txt >> /tmp/existing_cron
crontab /tmp/existing_cron
```

Cron output is appended to `logs/cron.log`.

---

## Outreach Agent

The outreach agent reads scored leads from your Google Sheet, fetches each lead's GitHub README, uses Claude to generate a personalized cold email, lets you review and approve them in the terminal, and sends approved emails via Gmail SMTP. The entire pipeline is a stateful LangGraph graph with a human-in-the-loop checkpoint between generation and sending.

---

### Prerequisites

Before setting up the outreach agent you must have completed the lead generation setup above — the outreach agent reads from the same Google Sheet that `run.py` writes to.

---

### Step 1 — Install the additional dependencies

```bash
pip install -r requirements.txt
```

The outreach agent adds `langgraph`, `langchain-core`, `anthropic`, and `langgraph-checkpoint-sqlite` on top of the existing packages. Running the command above installs everything.

---

### Step 2 — Use your Gmail account

The agent sends emails from a Gmail account. Use your existing personal Gmail — no new account needed.

---

### Step 3 — Generate a Gmail app password

Google requires an app password for SMTP access (your regular Gmail password will not work).

1. Enable 2-Step Verification on your Google account at [myaccount.google.com/security](https://myaccount.google.com/security) (required)
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select **Mail** and click **Generate**
4. Google shows a 16-character password — copy it immediately (it is only shown once)
5. This is your `SMTP_PASSWORD` — paste it into `.env`

---

### Step 4 — Get an Anthropic API key

1. Go to [https://console.anthropic.com](https://console.anthropic.com) and sign in or create an account
2. Navigate to **API Keys** and click **Create Key**
3. Copy the key (starts with `sk-ant-`)
4. Paste it into `ANTHROPIC_API_KEY` in your `.env` file

Cost is approximately **$0.15 per 10-email batch** using Claude Sonnet.

---

### Step 5 — Add outreach variables to your `.env` file

Open your `.env` file and add the following block:

```bash
# ── Outreach agent ────────────────────────────────────────
# Gmail SMTP credentials
SMTP_USERNAME=yourgmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# Sender identity (shown in From header of every email)
SENDER_NAME=Fayzan and Dilraj, Co-founders of Chox
SENDER_EMAIL=yourgmail@gmail.com
```

**Required:** `SMTP_USERNAME`, `SMTP_PASSWORD`, `ANTHROPIC_API_KEY` — the agent refuses to start if any of these are missing.

**Optional:** `SENDER_NAME`, `SENDER_EMAIL` — these have defaults but you should set them explicitly.

---

### Step 6 — Review send limits in `outreach/outreach_config.py`

Open `outreach/outreach_config.py` and check these two values:

```python
BATCH_SIZE = 10          # emails generated and reviewed per run
MAX_EMAILS_PER_DAY = 20  # hard ceiling on sends per calendar day
```

**If this is your first week sending**, lower `MAX_EMAILS_PER_DAY` to `5`. Sending 20 cold emails per day from a Gmail account on day one will get you flagged as spam. Ramp up gradually:

| Week | Recommended `MAX_EMAILS_PER_DAY` |
| ---- | -------------------------------- |
| 1–2  | 5                                |
| 3–4  | 10                               |
| 5+   | 15–20                            |

---

### Step 7 — Verify setup with a dry run

A dry run executes the full pipeline — loads leads, fetches READMEs, generates emails, presents them for your review — but skips the actual send. Nothing is emailed and the Google Sheet is not updated.

```bash
python run_outreach.py --dry-run
```

What you will see:

1. Config validation (fails fast if any required env var is missing)
2. A business hours warning if you are running outside Mon–Fri 9am–5pm (advisory only)
3. Lead loading from the Google Sheet
4. GitHub README fetching (one API call per lead, rate-limited)
5. Claude generating emails for each lead
6. The review terminal — one email at a time with lead context

In the review terminal, your options for each email are:

| Key | Action                                                                               |
| --- | ------------------------------------------------------------------------------------ |
| `A` | Approve this email                                                                   |
| `R` | Reject this email (lead stays uncontacted, available for the next run)               |
| `E` | Edit the email body in `$EDITOR` (defaults to nano), then approve the edited version |
| `B` | Approve this email and all remaining emails in the batch — no more prompts           |
| `Q` | Quit — saves state to checkpoint, no emails sent, resume later with `--resume`       |

After reviewing, the dry run prints a summary of what **would** have been sent and exits.

If anything errors during the dry run, fix it before running live.

---

### Step 8 — Run live

```bash
python run_outreach.py
```

Same flow as the dry run, except after review it:

1. Sends approved emails via Gmail SMTP with 90–180 second randomized delays between each send
2. Writes back `contacted=TRUE`, `contacted_at`, and `contact_method=email` to the Google Sheet for every successfully sent lead
3. Marks bounced addresses as `response_status=bounced` in the sheet
4. Prints a run summary (sent / failed / bounced / rejected counts)

**Tip:** Review the first 2–3 emails carefully before pressing `B` to bulk-approve. Once you are confident in the email quality, `B` after a spot-check is the normal workflow.

---

### Resuming an interrupted run

If you press `Q` during review or hit `Ctrl-C` at any point, the pipeline state is saved to `ghostline_outreach.db` in the project root. Resume from exactly where you left off:

```bash
python run_outreach.py --resume
```

The resume picks up the already-generated emails — it does not re-fetch READMEs or re-call Claude.

---

### Other flags

```bash
# Override batch size for this run only (does not change config)
python run_outreach.py --batch-size 5

# Combine flags
python run_outreach.py --dry-run --batch-size 3
```

---

### Outreach environment variables

| Variable            | Required | Description                                                           | Example                                  |
| ------------------- | -------- | --------------------------------------------------------------------- | ---------------------------------------- |
| `SMTP_USERNAME`     | Yes      | Your Gmail address                                                    | `you@gmail.com`                          |
| `SMTP_PASSWORD`     | Yes      | Gmail app password (16 chars, from myaccount.google.com/apppasswords) | `abcd efgh ijkl mnop`                    |
| `ANTHROPIC_API_KEY` | Yes      | Anthropic API key for Claude                                          | `sk-ant-xxxx`                            |
| `SENDER_NAME`       | No       | Display name in the From header                                       | `Fayzan and Dilraj, Co-founders of Chox` |
| `SENDER_EMAIL`      | No       | Reply-To address (defaults to SMTP_USERNAME)                          | `you@gmail.com`                          |

---

### Outreach troubleshooting

| Error                                      | Cause                                                                      | Fix                                                               |
| ------------------------------------------ | -------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `Missing required environment variable(s)` | `SMTP_USERNAME`, `SMTP_PASSWORD`, or `ANTHROPIC_API_KEY` not set in `.env` | Add the missing variable(s) and re-run                            |
| `SMTPAuthenticationError`                  | App password is wrong or 2FA is not enabled on the Gmail account           | Re-generate the app password at myaccount.google.com/apppasswords |
| `No uncontacted leads available`           | All leads in the sheet have already been contacted                         | Run `python run.py` to discover new leads first                   |
| `No checkpoint found for today's thread`   | Used `--resume` but no run has been started today                          | Run without `--resume` to start a fresh pipeline                  |
| `ModuleNotFoundError: langgraph`           | Dependencies not installed                                                 | Run `pip install -r requirements.txt`                             |
| Emails generating but all look generic     | README fetch failed for most leads (404s)                                  | Check GitHub token is set and valid in `.env`                     |
| `Editor 'X' not found`                     | `$EDITOR` env var points to a binary that does not exist                   | Run `export EDITOR=nano` before running the agent                 |

---

## Troubleshooting

| Error                                    | Cause                                                                         | Fix                                                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `Failed to authenticate with GitHub API` | `GITHUB_TOKEN` is missing, empty, or invalid                                  | Verify the token at [github.com/settings/tokens](https://github.com/settings/tokens) and update `.env`      |
| `Spreadsheet not found`                  | `SPREADSHEET_ID` is wrong or the sheet is not shared with the service account | Double-check the ID in the sheet URL and confirm the sheet is shared with the service account email         |
| `Service account file not found`         | The JSON key file path in `SERVICE_ACCOUNT_FILE` does not exist               | Verify the file is in the project root or update the path in `.env`                                         |
| `Core API budget critically low`         | GitHub rate limit exhausted during the run                                    | Wait for the rate limit to reset (check `X-RateLimit-Reset` header) and run again                           |
| `No new leads found`                     | Normal if the tool ran recently                                               | Leads are deduplicated by GitHub username. New leads appear as new developers push LangChain/LangGraph code |
