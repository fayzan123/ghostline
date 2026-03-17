"""
discover.py — Repository discovery via GitHub search API for the
Ghostline lead generation tool.
"""

from github_client import GitHubClient
from config import SEARCH_QUERIES, PAGES_PER_QUERY


def discover_repos(client: GitHubClient) -> list[dict]:
    """
    Search GitHub for repos matching LangChain/LangGraph queries.

    For each query in SEARCH_QUERIES, paginates up to PAGES_PER_QUERY pages
    (per_page=100). Deduplicates results by repo full_name.

    Args:
        client: Authenticated GitHubClient instance

    Returns:
        List of unique repo dicts from the GitHub search API response items.
        Each dict has at minimum: full_name, html_url, description, fork,
        stargazers_count, language, pushed_at, owner.login, topics.

    Edge cases:
        - Queries returning 0 results are silently skipped.
        - total_count may exceed 1000 but API caps at 1000; paginate only to that limit.
        - Empty items array signals no more results for that page.
    """
    pass
