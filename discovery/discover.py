"""
discover.py — Repository discovery via GitHub search API for the
Ghostline lead generation tool.
"""

import logging

from discovery.github_client import GitHubClient
from shared.config import SEARCH_QUERIES, PAGES_PER_QUERY

logger = logging.getLogger(__name__)


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
    seen = {}  # keyed on repo full_name for deduplication

    for query in SEARCH_QUERIES:
        logger.info("Searching: %s", query)

        for page in range(1, PAGES_PER_QUERY + 1):
            data = client.search_repos(query, page=page)

            if not data:
                logger.debug("Empty response for query=%r page=%d, skipping.", query, page)
                break

            items = data.get("items", [])
            total_count = data.get("total_count", 0)

            if not items:
                logger.debug(
                    "No items on page %d for query=%r (total_count=%d), stopping pagination.",
                    page,
                    query,
                    total_count,
                )
                break

            for repo in items:
                full_name = repo.get("full_name")
                if full_name and full_name not in seen:
                    seen[full_name] = repo

            logger.info(
                "  Page %d: %d items (total_count=%d, unique so far=%d)",
                page,
                len(items),
                total_count,
                len(seen),
            )

            # GitHub search API caps results at 1000 — stop if we have reached that
            if page * 100 >= min(total_count, 1000):
                break

    logger.info("Discovery complete: %d unique repos from %d queries.", len(seen), len(SEARCH_QUERIES))
    return list(seen.values())


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    client = GitHubClient()
    repos = discover_repos(client)

    print(f"\nDiscovered {len(repos)} unique repositories.\n")

    for repo in repos[:3]:
        print(f"  {repo['full_name']}  ({repo.get('stargazers_count', 0)} stars)")
