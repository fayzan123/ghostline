à# Ghostline

Automated GitHub lead generation tool for Chox. Discovers developers actively building with LangChain and LangGraph, extracts their public contact information, scores them against a multi-signal framework, and exports qualified leads to Google Sheets daily.

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
./run.sh
```

This activates the virtual environment, runs the pipeline, and logs output to `logs/run_YYYY-MM-DD.log`.

**Cron setup (runs daily at 6:00 AM):**

```bash
# Review the cron schedule
cat cron.txt

# Install (replaces existing crontab)
crontab cron.txt

# Or merge into existing crontab
crontab -l > /tmp/existing_cron
cat cron.txt >> /tmp/existing_cron
crontab /tmp/existing_cron
```

Cron output is appended to `logs/cron.log`.

## Troubleshooting

| Error                                    | Cause                                                                         | Fix                                                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `Failed to authenticate with GitHub API` | `GITHUB_TOKEN` is missing, empty, or invalid                                  | Verify the token at [github.com/settings/tokens](https://github.com/settings/tokens) and update `.env`      |
| `Spreadsheet not found`                  | `SPREADSHEET_ID` is wrong or the sheet is not shared with the service account | Double-check the ID in the sheet URL and confirm the sheet is shared with the service account email         |
| `Service account file not found`         | The JSON key file path in `SERVICE_ACCOUNT_FILE` does not exist               | Verify the file is in the project root or update the path in `.env`                                         |
| `Core API budget critically low`         | GitHub rate limit exhausted during the run                                    | Wait for the rate limit to reset (check `X-RateLimit-Reset` header) and run again                           |
| `No new leads found`                     | Normal if the tool ran recently                                               | Leads are deduplicated by GitHub username. New leads appear as new developers push LangChain/LangGraph code |
