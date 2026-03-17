"""
report.py — Run summary reporting for the Ghostline lead generation tool.
"""

import time
from config import RUN_ID


def print_report(stats: dict) -> None:
    """
    Print formatted run summary to stdout and append to runs.log.

    Expected stats dict keys:
        repos_discovered: int
        repos_qualified: int
        users_processed: int
        emails_found: int
        tier1_leads: int
        tier2_leads: int
        new_leads_added: int
        already_in_sheet: int
        api_calls_used: int
        run_duration_seconds: float

    Output format:
        === Ghostline Run Report ({RUN_ID}) ===
        Repos discovered:      {repos_discovered}
        Repos qualified:       {repos_qualified}
        Users processed:       {users_processed}
        Emails found:          {emails_found}
          - Tier 1 leads:      {tier1_leads}
          - Tier 2 leads:      {tier2_leads}
        New leads added:       {new_leads_added}
        Already in sheet:      {already_in_sheet}
        API calls used:        {api_calls_used}
        Run duration:          {run_duration_seconds:.1f}s
        ========================================

    Appends the same summary to runs.log with a blank line separator.
    """
    pass
