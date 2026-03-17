"""
qualify.py — Repository qualification and filtering for the
Ghostline lead generation tool.
"""

from github_client import GitHubClient
from config import TUTORIAL_ORG_BLOCKLIST, REPO_NAME_BLOCKLIST, DESCRIPTION_BLOCKLIST


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
    pass
