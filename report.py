"""
report.py — Run summary reporting for the Ghostline lead generation tool.
"""

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
    """
    report = (
        f"=== Ghostline Run Report ({RUN_ID}) ===\n"
        f"Repos discovered:      {stats.get('repos_discovered', 0)}\n"
        f"Repos qualified:       {stats.get('repos_qualified', 0)}\n"
        f"Users processed:       {stats.get('users_processed', 0)}\n"
        f"Emails found:          {stats.get('emails_found', 0)}\n"
        f"  - Tier 1 leads:      {stats.get('tier1_leads', 0)}\n"
        f"  - Tier 2 leads:      {stats.get('tier2_leads', 0)}\n"
        f"New leads added:       {stats.get('new_leads_added', 0)}\n"
        f"Already in sheet:      {stats.get('already_in_sheet', 0)}\n"
        f"API calls used:        {stats.get('api_calls_used', 0)}\n"
        f"Run duration:          {stats.get('run_duration_seconds', 0.0):.1f}s\n"
        f"========================================"
    )

    print(report)

    # Append to runs.log
    with open("runs.log", "a") as f:
        f.write("\n" + report + "\n")
