"""
extract_email.py — Email extraction and validation for the
Ghostline lead generation tool.
"""

import logging
import re
from collections import Counter

from github_client import GitHubClient
from models import Lead
from config import INVALID_EMAIL_PATTERNS, EMAIL_REGEX, RUN_ID

logger = logging.getLogger(__name__)

FREEMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}


def extract_emails(repos: list[dict], client: GitHubClient, existing_users: set) -> list[Lead]:
    """
    For each unique repo owner not already in the sheet, attempt to find a public email.
    Returns partially-filled Lead objects (score/tier/pain_point filled later by score.py).

    Email extraction fallback chain (stop on first valid email):
        1. GitHub user profile API — check 'email' field
        2. Repo commit metadata — parse commit.author.email from recent commits
        3. User public events API — parse PushEvent payload.commits[].author.email
        4. Profile bio regex — parse 'bio' field for email pattern

    All found emails are validated against INVALID_EMAIL_PATTERNS before use.
    If multiple valid emails found, prefer: profile > most frequent commit email > non-freemail.

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
    Run the four-method email fallback chain for a single user.
    Returns a Lead if a valid email is found, otherwise None.
    """
    # --- Method 1: GitHub user profile ---
    user_profile = client.get_user(username)
    if not user_profile:
        logger.debug("Could not fetch profile for %s, skipping.", username)
        return None

    profile_email = user_profile.get("email")
    candidate_emails: dict[str, str] = {}  # email -> source
    commit_email_counter: Counter = Counter()

    if profile_email and is_valid_email(profile_email):
        candidate_emails[profile_email] = "profile"

    # --- Method 2: Commit metadata from best repo ---
    repo_full_name = repo.get("full_name", "")
    if "/" in repo_full_name:
        owner_name, repo_name = repo_full_name.split("/", 1)
    else:
        owner_name = username
        repo_name = repo.get("name", "")

    if repo_name:
        commits = client.get_commits(owner_name, repo_name, username)
        for commit_obj in commits:
            commit_data = commit_obj.get("commit", {})
            for field_key in ("author", "committer"):
                email = commit_data.get(field_key, {}).get("email")
                if email and is_valid_email(email):
                    commit_email_counter[email] += 1
                    if email not in candidate_emails:
                        candidate_emails[email] = "commits"

    # --- Method 3: User public events ---
    events = client.get_user_events(username)
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        payload_commits = event.get("payload", {}).get("commits", [])
        for pc in payload_commits:
            email = pc.get("author", {}).get("email")
            if email and is_valid_email(email):
                commit_email_counter[email] += 1
                if email not in candidate_emails:
                    candidate_emails[email] = "events"

    # --- Method 4: Bio regex ---
    bio = user_profile.get("bio") or ""
    bio_email = extract_email_from_bio(bio)
    if bio_email and bio_email not in candidate_emails:
        candidate_emails[bio_email] = "bio"

    # --- Pick the best email ---
    if not candidate_emails:
        return None

    best_email, best_source = _pick_best_email(candidate_emails, commit_email_counter)
    if not best_email:
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
        run_id=RUN_ID,
    )


def _pick_best_email(
    candidate_emails: dict[str, str],
    commit_email_counter: Counter,
) -> tuple[str, str]:
    """
    From collected candidate emails, pick the best one using the preference order:
      1. Profile email (user explicitly chose to make it public)
      2. Most frequently occurring email across commits
      3. Non-freemail addresses over freemail
    Returns (email, source) tuple, or ("", "") if nothing qualifies.
    """
    # Preference 1: profile email
    for email, source in candidate_emails.items():
        if source == "profile":
            return email, source

    # Preference 2: most frequent commit email
    # Filter commit_email_counter to only valid candidates
    commit_candidates = {
        e: count for e, count in commit_email_counter.items() if e in candidate_emails
    }
    if commit_candidates:
        # Sort by frequency descending, then prefer non-freemail as tiebreaker
        sorted_commits = sorted(
            commit_candidates.items(),
            key=lambda x: (x[1], _is_not_freemail(x[0])),
            reverse=True,
        )
        best_commit_email = sorted_commits[0][0]
        return best_commit_email, candidate_emails[best_commit_email]

    # Preference 3: non-freemail over freemail among remaining candidates
    non_free = [e for e in candidate_emails if _is_not_freemail(e)]
    if non_free:
        email = non_free[0]
        return email, candidate_emails[email]

    # Fallback: return whichever email we have
    email = next(iter(candidate_emails))
    return email, candidate_emails[email]


def _is_not_freemail(email: str) -> bool:
    """Return True if the email domain is NOT a common freemail provider."""
    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    return domain not in FREEMAIL_DOMAINS


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
