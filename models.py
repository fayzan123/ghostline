"""
models.py — Data models for the Ghostline lead generation tool.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Lead:
    github_username: str
    email: str
    full_name: str = ""
    repo_url: str = ""
    repo_name: str = ""
    repo_description: str = ""
    repo_stars: int = 0
    repo_language: str = ""
    frameworks_detected: str = ""      # comma-separated
    lead_score: int = 0
    lead_tier: str = ""                # "tier_1" or "tier_2"
    inferred_pain_point: str = ""      # "financial_risk", etc.
    risk_apis_detected: str = ""       # comma-separated
    profile_bio: str = ""
    profile_company: str = ""
    profile_location: str = ""
    profile_blog: str = ""
    twitter_handle: str = ""
    followers: int = 0
    public_repos: int = 0
    email_source: str = ""             # "profile", "commits", "events", "bio"
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contacted: str = "FALSE"
    contacted_at: str = ""
    contact_method: str = ""
    response_status: str = "none"
    notes: str = ""
    run_id: str = ""

    def to_row(self) -> list:
        """Convert to list for Google Sheets append_rows(). Order matches GOOGLE_SHEET_HEADERS."""
        return [
            self.github_username, self.email, self.full_name,
            self.repo_url, self.repo_name, self.repo_description,
            self.repo_stars, self.repo_language, self.frameworks_detected,
            self.lead_score, self.lead_tier, self.inferred_pain_point,
            self.risk_apis_detected, self.profile_bio, self.profile_company,
            self.profile_location, self.profile_blog, self.twitter_handle,
            self.followers, self.public_repos, self.email_source,
            self.discovered_at, self.contacted, self.contacted_at,
            self.contact_method, self.response_status, self.notes,
            self.run_id,
        ]
