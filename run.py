#!/usr/bin/env python3
"""
Chox Lead Generation Tool
Run: python run.py

Finds 50-100 qualified LangChain/LangGraph developers on GitHub daily,
extracts their public emails, scores them, and appends to Google Sheets.
"""

import sys
import time

import config
from github_client import GitHubClient
from discover import discover_repos
from qualify import qualify_repos
from extract_email import extract_emails
from score import score_leads
from sheets import connect_to_sheet, load_existing_usernames, append_leads
from report import print_report


def main():
    start_time = time.time()
    stats = {
        "repos_discovered": 0,
        "repos_qualified": 0,
        "users_processed": 0,
        "emails_found": 0,
        "tier1_leads": 0,
        "tier2_leads": 0,
        "new_leads_added": 0,
        "already_in_sheet": 0,
        "api_calls_used": 0,
        "run_duration_seconds": 0.0,
    }

    try:
        # STEP 1: INITIALIZE
        # Verify GitHub auth via GET /rate_limit — exit with clear error if auth fails
        client = GitHubClient()
        pass  # TODO: client.check_rate_limit() and abort if auth fails

        # Connect to Google Sheets and load existing usernames for dedup
        spreadsheet, worksheet = connect_to_sheet()
        existing_users = load_existing_usernames(worksheet)
        pass  # TODO: log existing_users count

        # STEP 2: DISCOVER REPOSITORIES
        # Search GitHub for repos matching LangChain/LangGraph queries (6 queries x 3 pages)
        raw_repos = discover_repos(client)
        stats["repos_discovered"] = len(raw_repos)
        pass  # TODO: print(f"Discovered {len(raw_repos)} unique repositories")

        # STEP 3: QUALIFY REPOSITORIES
        # Filter forks, tutorials, demos, official repos; verify imports on borderline cases
        qualified_repos = qualify_repos(raw_repos, client)
        stats["repos_qualified"] = len(qualified_repos)
        pass  # TODO: print(f"Qualified {len(qualified_repos)} repositories")

        # STEP 4: EXTRACT EMAILS & ENRICH PROFILES
        # Run 4-method fallback chain per user; build Lead objects for those with valid emails
        leads_with_emails = extract_emails(qualified_repos, client, existing_users)
        stats["users_processed"] = len(set(r["owner"]["login"] for r in qualified_repos))
        stats["emails_found"] = len(leads_with_emails)
        pass  # TODO: print(f"Extracted emails for {len(leads_with_emails)} users")

        # STEP 5: SCORE & CLASSIFY LEADS
        # Run scoring algorithm; assign tier_1/tier_2; infer pain point; drop score < TIER2_THRESHOLD
        scored_leads = score_leads(leads_with_emails)
        stats["tier1_leads"] = sum(1 for l in scored_leads if l.lead_tier == "tier_1")
        stats["tier2_leads"] = sum(1 for l in scored_leads if l.lead_tier == "tier_2")
        pass  # TODO: print(f"Scored {len(scored_leads)} leads")

        # STEP 6: WRITE TO GOOGLE SHEETS
        # Deduplicate against sheet, batch-append new leads via append_rows()
        new_count = append_leads(worksheet, scored_leads, existing_users)
        stats["new_leads_added"] = new_count
        stats["already_in_sheet"] = len(scored_leads) - new_count
        pass  # TODO: print(f"Added {new_count} new leads to sheet")

        # STEP 7: REPORT
        # Print formatted summary to stdout and append to runs.log
        stats["run_duration_seconds"] = time.time() - start_time
        print_report(stats)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nRun interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Run failed: {e}")
        stats["run_duration_seconds"] = time.time() - start_time
        print_report(stats)
        sys.exit(1)


if __name__ == "__main__":
    main()
