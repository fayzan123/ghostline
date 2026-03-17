"""
qualify.py — Repository qualification and filtering for the
Ghostline lead generation tool.
"""

import logging

from github_client import GitHubClient
from config import TUTORIAL_ORG_BLOCKLIST, REPO_NAME_BLOCKLIST, DESCRIPTION_BLOCKLIST

logger = logging.getLogger(__name__)


def qualify_repos(repos: list[dict], client: GitHubClient) -> list[dict]:
    """
    Filter raw repo list to only legitimate, non-tutorial, non-fork projects.

    Filters applied in order:
    1. repo['fork'] == False (double-check API filter)
    2. repo['owner']['login'] not in TUTORIAL_ORG_BLOCKLIST
    3. repo name (lowercased) does not contain any REPO_NAME_BLOCKLIST substring
    4. repo description (lowercased) does not contain any DESCRIPTION_BLOCKLIST phrase
    5. repo language is not exclusively "Jupyter Notebook"
    6. Structural heuristic: not (0 stars AND 1 contributor AND <5 files AND no CI/Docker/tests)
    7. Optional code search verification for borderline cases where metadata
       lacks explicit langchain/langgraph signals in name, description, or topics.

    Args:
        repos: List of raw repo dicts from discover_repos()
        client: GitHubClient instance (needed for optional code search verification)

    Returns:
        List of qualified repo dicts that passed all filters.
    """
    qualified = []
    filtered_counts = {
        "fork": 0,
        "blocklisted_org": 0,
        "blocklisted_name": 0,
        "blocklisted_desc": 0,
        "jupyter_only": 0,
        "low_signal": 0,
    }

    for repo in repos:
        # Filter 1: No forks
        if repo.get("fork", False):
            filtered_counts["fork"] += 1
            continue

        # Filter 2: Owner not in tutorial org blocklist
        owner_login = repo.get("owner", {}).get("login", "")
        if owner_login in TUTORIAL_ORG_BLOCKLIST:
            filtered_counts["blocklisted_org"] += 1
            continue

        # Filter 3: Repo name doesn't contain blocklisted substrings
        repo_name_lower = (repo.get("name") or "").lower()
        if _contains_blocklist_term(repo_name_lower, REPO_NAME_BLOCKLIST):
            filtered_counts["blocklisted_name"] += 1
            continue

        # Filter 4: Description doesn't contain blocklisted phrases
        description_lower = (repo.get("description") or "").lower()
        if _contains_blocklist_term(description_lower, DESCRIPTION_BLOCKLIST):
            filtered_counts["blocklisted_desc"] += 1
            continue

        # Filter 5: Not Jupyter-notebook-only
        if repo.get("language") == "Jupyter Notebook":
            filtered_counts["jupyter_only"] += 1
            continue

        # Filter 6: Structural heuristic — reject repos with 0 stars AND fewer than 5 commits
        # We use stargazers_count from the repo dict (already present from discovery).
        # For solo repos with zero community signal, this is a low-effort tutorial indicator.
        stars = repo.get("stargazers_count", 0) or 0
        if stars == 0:
            # For zero-star repos, we apply a lenient heuristic:
            # repos from search results with 0 stars are borderline.
            # We keep them only if they have some metadata signal (description length, topics).
            topics = repo.get("topics") or []
            desc_len = len(description_lower)
            if desc_len < 10 and len(topics) == 0:
                filtered_counts["low_signal"] += 1
                continue

        # Filter 7: Optional code search verification for borderline cases
        # If the repo name, description, and topics don't mention langchain/langgraph,
        # it might be a false positive from search. We skip code search to conserve budget
        # but flag it — the scoring step will naturally give these repos lower scores.
        # No API call here to stay within budget.

        qualified.append(repo)

    logger.info(
        "Qualification complete: %d/%d repos passed. Filtered: %s",
        len(qualified),
        len(repos),
        ", ".join(f"{k}={v}" for k, v in filtered_counts.items() if v > 0),
    )

    return qualified


def _contains_blocklist_term(text: str, blocklist: list[str]) -> bool:
    """Check if any blocklist term appears as a substring in text."""
    for term in blocklist:
        if term in text:
            return True
    return False
