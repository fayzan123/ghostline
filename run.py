#!/usr/bin/env python3
"""
Ghostline Lead Generation Tool
Run: python run.py

Finds 50-100 qualified LangChain/LangGraph developers on GitHub daily,
extracts their public emails, scores them, and appends to Google Sheets.
"""

import logging
import sys
import time
import traceback

import config
from github_client import GitHubClient
from discover import discover_repos
from qualify import qualify_repos
from extract_email import extract_emails
from score import score_leads
from sheets import connect_to_sheet, load_existing_usernames, append_leads
from report import print_report

logger = logging.getLogger(__name__)


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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

    client = None

    try:
        # ==================================================================
        # STEP 1: INITIALIZE
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 1: INITIALIZE")
        logger.info("=" * 60)

        # Verify GitHub auth via GET /rate_limit (happens in __init__)
        client = GitHubClient()

        # Connect to Google Sheets and load existing usernames for dedup
        spreadsheet, worksheet = connect_to_sheet()
        existing_users = load_existing_usernames(worksheet)
        logger.info("Existing leads in sheet: %d", len(existing_users))

        # ==================================================================
        # STEP 2: DISCOVER REPOSITORIES
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 2: DISCOVER REPOSITORIES")
        logger.info("=" * 60)

        raw_repos = discover_repos(client)
        stats["repos_discovered"] = len(raw_repos)
        logger.info("Discovered %d unique repositories.", len(raw_repos))

        # ==================================================================
        # STEP 3: QUALIFY REPOSITORIES
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 3: QUALIFY REPOSITORIES")
        logger.info("=" * 60)

        qualified_repos = qualify_repos(raw_repos, client)
        stats["repos_qualified"] = len(qualified_repos)
        logger.info("Qualified %d repositories.", len(qualified_repos))

        if len(qualified_repos) > config.MAX_LEADS_PER_RUN:
            logger.info("Capping qualified repos from %d to %d", len(qualified_repos), config.MAX_LEADS_PER_RUN)
            qualified_repos = qualified_repos[:config.MAX_LEADS_PER_RUN]

        # ==================================================================
        # STEP 4: EXTRACT EMAILS & ENRICH PROFILES
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 4: EXTRACT EMAILS & ENRICH PROFILES")
        logger.info("=" * 60)

        leads_with_emails = extract_emails(qualified_repos, client, existing_users)
        stats["users_processed"] = len(
            set(r.get("owner", {}).get("login", "") for r in qualified_repos if r.get("owner", {}).get("login"))
        )
        stats["emails_found"] = len(leads_with_emails)
        logger.info(
            "Processed %d unique users, extracted %d emails.",
            stats["users_processed"],
            stats["emails_found"],
        )

        # ==================================================================
        # STEP 5: SCORE & CLASSIFY LEADS
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 5: SCORE & CLASSIFY LEADS")
        logger.info("=" * 60)

        scored_leads = score_leads(leads_with_emails)
        stats["tier1_leads"] = sum(1 for l in scored_leads if l.lead_tier == "tier_1")
        stats["tier2_leads"] = sum(1 for l in scored_leads if l.lead_tier == "tier_2")
        logger.info(
            "Scored %d leads: %d tier-1, %d tier-2.",
            len(scored_leads),
            stats["tier1_leads"],
            stats["tier2_leads"],
        )

        # ==================================================================
        # STEP 6: WRITE TO GOOGLE SHEETS
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 6: WRITE TO GOOGLE SHEETS")
        logger.info("=" * 60)

        new_count = append_leads(worksheet, scored_leads, existing_users)
        stats["new_leads_added"] = new_count
        stats["already_in_sheet"] = len(scored_leads) - new_count
        logger.info("Added %d new leads to sheet.", new_count)

        # ==================================================================
        # STEP 7: REPORT
        # ==================================================================
        logger.info("=" * 60)
        logger.info("STEP 7: REPORT")
        logger.info("=" * 60)

        stats["api_calls_used"] = client.api_call_count
        stats["run_duration_seconds"] = time.time() - start_time
        print_report(stats)

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Run interrupted by user.")
        stats["api_calls_used"] = client.api_call_count if client else 0
        stats["run_duration_seconds"] = time.time() - start_time
        print_report(stats)
        sys.exit(1)

    except Exception:
        logger.error("Run failed with unhandled exception:\n%s", traceback.format_exc())
        stats["api_calls_used"] = client.api_call_count if client else 0
        stats["run_duration_seconds"] = time.time() - start_time
        print_report(stats)
        sys.exit(1)


if __name__ == "__main__":
    main()
