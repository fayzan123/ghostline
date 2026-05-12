"""
extract_email.py — Email extraction and validation for the
Ghostline lead generation tool.
"""

import logging
import re

from discovery.github_client import GitHubClient
from shared.models import Lead
from shared.config import INVALID_EMAIL_PATTERNS, EMAIL_REGEX, RUN_ID, IMPORT_TO_CATEGORY

logger = logging.getLogger(__name__)


def extract_emails(repos: list[dict], client: GitHubClient, existing_users: set) -> list[Lead]:
    """
    For each unique repo owner not already in the sheet, attempt to find a public email.
    Returns partially-filled Lead objects (score/tier/pain_point filled later by score.py).

    Email extraction sources (only data the user explicitly chose to make public):
        1. GitHub user profile API — 'email' field (user set this themselves)
        2. Profile bio regex — 'bio' field, which the user wrote and published

    We deliberately do NOT scrape commit author emails or PushEvent payloads.
    Those are technically public but most users do not realize their commit
    email is exposed, and GitHub's Acceptable Use Policy forbids using such
    data for unsolicited email. Profile-published emails are consent-based.

    All found emails are validated against INVALID_EMAIL_PATTERNS before use.
    If both sources yield an email, the profile email wins.

    Args:
        repos: List of qualified repo dicts from qualify_repos()
        client: Authenticated GitHubClient instance
        existing_users: Set of github_username strings already in the Google Sheet

    Returns:
        List of Lead objects with email, profile data, and repo data populated.
        Only leads with a valid, resolved email are included.
    """
    # --- Step 1: Collect unique usernames and their best repo (highest stars) ---
    user_best_repo: dict[str, dict] = {}
    for repo in repos:
        owner = repo.get("owner", {})
        username = owner.get("login")
        if not username:
            continue
        if username in existing_users:
            continue
        stars = repo.get("stargazers_count", 0) or 0
        if username not in user_best_repo or stars > (user_best_repo[username].get("stargazers_count", 0) or 0):
            user_best_repo[username] = repo

    logger.info(
        "Email extraction: %d unique new users to process (skipped %d existing).",
        len(user_best_repo),
        len(set(r.get("owner", {}).get("login", "") for r in repos) & existing_users),
    )

    leads: list[Lead] = []

    for username, repo in user_best_repo.items():
        lead = _process_user(username, repo, client)
        if lead is not None:
            leads.append(lead)
            logger.info(
                "  [+] %s -> %s (source: %s)", username, lead.email, lead.email_source
            )
        else:
            logger.debug("  [-] %s -> no valid email found", username)

    logger.info("Email extraction complete: %d leads with emails.", len(leads))
    return leads


def _process_user(username: str, repo: dict, client: GitHubClient) -> Lead | None:
    """
    Resolve a consent-based public email for a single user.
    Returns a Lead if a valid email is found, otherwise None.
    """
    user_profile = client.get_user(username)
    if not user_profile:
        logger.debug("Could not fetch profile for %s, skipping.", username)
        return None

    bio = user_profile.get("bio") or ""

    profile_email = user_profile.get("email")
    if profile_email and is_valid_email(profile_email):
        best_email, best_source = profile_email, "profile"
    else:
        bio_email = extract_email_from_bio(bio)
        if bio_email:
            best_email, best_source = bio_email, "bio"
        else:
            return None

    # --- Build Lead ---
    description_raw = repo.get("description") or ""
    description = description_raw[:200] if description_raw else ""

    topics = repo.get("topics", []) or []
    repo_name_lower = (repo.get("name") or "").lower()
    desc_lower = description_raw.lower()
    topics_lower = " ".join(t.lower() for t in topics)
    searchable = f"{repo_name_lower} {desc_lower} {topics_lower}"

    frameworks = []
    if "langchain" in searchable:
        frameworks.append("langchain")
    if "langgraph" in searchable:
        frameworks.append("langgraph")

    # Detect risk APIs from repo metadata
    risk_apis = []
    for api_key in IMPORT_TO_CATEGORY:
        if api_key.lower() in searchable:
            risk_apis.append(api_key)

    return Lead(
        github_username=username,
        email=best_email,
        email_source=best_source,
        full_name=user_profile.get("name") or "",
        profile_bio=bio,
        profile_company=user_profile.get("company") or "",
        profile_location=user_profile.get("location") or "",
        profile_blog=user_profile.get("blog") or "",
        twitter_handle=user_profile.get("twitter_username") or "",
        followers=user_profile.get("followers", 0) or 0,
        public_repos=user_profile.get("public_repos", 0) or 0,
        repo_url=repo.get("html_url") or "",
        repo_name=repo.get("full_name") or "",
        repo_description=description,
        repo_stars=repo.get("stargazers_count", 0) or 0,
        repo_language=repo.get("language") or "",
        frameworks_detected=", ".join(frameworks),
        risk_apis_detected=", ".join(risk_apis),
        run_id=RUN_ID,
    )


def is_valid_email(email: str) -> bool:
    """
    Check whether an email address is valid and not a known invalid pattern.

    Args:
        email: Email string to validate

    Returns:
        True if email matches EMAIL_REGEX and does not match any INVALID_EMAIL_PATTERNS.
        False otherwise.
    """
    if not email:
        return False

    if not re.fullmatch(EMAIL_REGEX, email):
        return False

    for pattern in INVALID_EMAIL_PATTERNS:
        if re.search(pattern, email):
            return False

    return True


def extract_email_from_bio(bio: str) -> str | None:
    """
    Regex-parse a GitHub profile bio for an email address.

    Args:
        bio: Raw bio string from GitHub user profile

    Returns:
        First valid email found in bio, or None.
    """
    if not bio:
        return None

    matches = re.findall(EMAIL_REGEX, bio)
    for email in matches:
        if is_valid_email(email):
            return email

    return None


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    client = GitHubClient()

    # Fake repo dict mimicking discover.py output for a well-known user
    fake_repo = {
        "full_name": "torvalds/linux",
        "name": "linux",
        "html_url": "https://github.com/torvalds/linux",
        "description": "Linux kernel source tree",
        "stargazers_count": 180000,
        "language": "C",
        "topics": [],
        "fork": False,
        "pushed_at": "2026-03-15T00:00:00Z",
        "owner": {
            "login": "torvalds",
            "type": "User",
        },
    }

    print("Running email extraction for torvalds (linux)...\n")
    results = extract_emails([fake_repo], client, set())

    if results:
        for lead in results:
            print(f"  Username:     {lead.github_username}")
            print(f"  Email:        {lead.email}")
            print(f"  Email Source: {lead.email_source}")
            print(f"  Full Name:    {lead.full_name}")
            print(f"  Followers:    {lead.followers}")
            print(f"  Repo:         {lead.repo_name} ({lead.repo_stars} stars)")
            print()
    else:
        print("  No leads with valid emails found.")
        print("  (This is expected if the user has no public email.)")
