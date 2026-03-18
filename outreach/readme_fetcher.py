"""
readme_fetcher.py — README retrieval layer for the Ghostline outreach agent.

Parses the repo_url field on a lead dict to extract the owner/repo slug, then
calls GitHubClient.get_readme() with the configured character limit.

A missing README (404 or network error) is treated as a non-fatal condition:
the error is logged and an empty string is returned so the email draft can
still be generated without README context.

Public interface:
  fetch_readme(lead, github_client) -> str
      Fetch one README.  Returns "" on any failure.

  fetch_readmes_batch(leads, github_client) -> dict[str, str]
      Fetch READMEs for a list of leads.  Maps repo_full_name -> README text.
      Individual failures do not abort the batch.
"""

import logging
from urllib.parse import urlparse

from discovery.github_client import GitHubClient
from outreach.outreach_config import README_MAX_CHARS

logger = logging.getLogger(__name__)


def _parse_repo_slug(repo_url: str) -> str | None:
    """
    Extract the 'owner/repo' slug from a full GitHub URL.

    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/   (trailing slash)
      https://github.com/owner/repo.git

    Returns:
        "owner/repo" string, or None if the URL cannot be parsed into a valid
        two-part slug.
    """
    if not repo_url:
        return None

    try:
        parsed = urlparse(repo_url)
        # Strip leading slash, trailing slash, and .git suffix
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]

        parts = path.split("/")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}/{parts[1]}"
    except Exception as exc:
        logger.warning("Failed to parse repo URL '%s': %s", repo_url, exc)

    return None


def fetch_readme(lead: dict, github_client: GitHubClient) -> str:
    """
    Fetch the README for a single lead's repository.

    Uses the lead's repo_url field to determine owner and repo name.
    Falls back to the repo_name field if repo_url is absent or unparseable,
    since repo_name is already stored as "owner/repo" in the sheet.

    Args:
        lead: A lead dict as returned by load_uncontacted_leads().  Must
              contain at least one of 'repo_url' or 'repo_name'.
        github_client: Caller-provided GitHubClient instance.

    Returns:
        README text truncated to README_MAX_CHARS, or "" on any error.
    """
    # Primary: parse from full URL
    slug = _parse_repo_slug(str(lead.get("repo_url", "")))

    # Fallback: repo_name is already "owner/repo" if the URL is missing
    if not slug:
        repo_name = str(lead.get("repo_name", "")).strip()
        parts = repo_name.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            slug = repo_name
            logger.debug(
                "repo_url missing or unparseable — using repo_name '%s' as slug.",
                slug,
            )

    if not slug:
        logger.warning(
            "Cannot determine repo slug for lead '%s' — skipping README fetch.",
            lead.get("github_username", "(unknown)"),
        )
        return ""

    owner, repo = slug.split("/", 1)

    try:
        readme_text = github_client.get_readme(owner, repo, max_chars=README_MAX_CHARS)
    except Exception as exc:
        # get_readme already logs internally, but catch anything unexpected here
        # so a single broken lead never kills the batch.
        logger.warning(
            "Unexpected error fetching README for %s: %s",
            slug,
            exc,
        )
        return ""

    if readme_text:
        logger.debug("Fetched README for %s (%d chars).", slug, len(readme_text))
    else:
        logger.debug("Empty README for %s.", slug)

    return readme_text


def fetch_readmes_batch(
    leads: list[dict],
    github_client: GitHubClient,
) -> dict[str, str]:
    """
    Fetch READMEs for a list of leads, returning a mapping of repo slug to
    README text.

    Progress is logged at INFO level so the caller can monitor throughput
    without enabling DEBUG.  Individual failures are logged and skipped — the
    batch always completes.

    Args:
        leads: List of lead dicts from load_uncontacted_leads().
        github_client: Caller-provided GitHubClient instance.

    Returns:
        Dict mapping "owner/repo" -> README text (possibly "").
        Leads whose slug cannot be determined are omitted from the result.
    """
    total = len(leads)
    results: dict[str, str] = {}

    for i, lead in enumerate(leads, start=1):
        username = lead.get("github_username", "(unknown)")

        # Resolve slug here (same logic as fetch_readme) so we can use it as
        # the dict key even when get_readme returns "".
        slug = _parse_repo_slug(str(lead.get("repo_url", "")))
        if not slug:
            repo_name = str(lead.get("repo_name", "")).strip()
            parts = repo_name.split("/")
            if len(parts) == 2 and parts[0] and parts[1]:
                slug = repo_name

        if not slug:
            logger.warning(
                "[%d/%d] Cannot determine repo slug for '%s' — skipping.",
                i, total, username,
            )
            continue

        logger.info(
            "[%d/%d] Fetching README for %s (%s).",
            i, total, slug, username,
        )

        readme_text = fetch_readme(lead, github_client)
        results[slug] = readme_text

    logger.info(
        "README fetch complete: %d/%d slugs resolved, %d non-empty.",
        len(results),
        total,
        sum(1 for v in results.values() if v),
    )

    return results
