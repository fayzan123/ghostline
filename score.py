"""
score.py — Lead scoring, tier assignment, and pain point inference for the
Ghostline lead generation tool.
"""

from models import Lead
from config import (
    TIER1_THRESHOLD,
    TIER2_THRESHOLD,
    PRODUCTION_KEYWORDS,
    MODERATE_KEYWORDS,
    TIER_A_IMPORTS,
    TIER_B_IMPORTS,
    TIER_C_IMPORTS,
    IMPORT_TO_CATEGORY,
)


def score_leads(leads: list[Lead]) -> list[Lead]:
    """
    Score each lead, assign tier, infer pain point. Filters out disqualified leads.

    For each lead, calls score_lead() and infer_pain_point(), then filters leads
    with score < TIER2_THRESHOLD (disqualified). Only leads scoring >= TIER2_THRESHOLD
    are returned.

    Implementation note: Full repo structure analysis (file tree for Dockerfile, CI, tests)
    costs 1 API call per repo. Only do this for repos scoring >= 20 from metadata signals.

    Args:
        leads: List of Lead objects from extract_emails() (score/tier fields are 0/"" at this point)

    Returns:
        List of Lead objects with lead_score, lead_tier, inferred_pain_point filled.
        Leads scoring < TIER2_THRESHOLD are excluded.
    """
    pass


def score_lead(lead_data: dict) -> int:
    """
    Calculate numeric lead score 0-100 using the four-category point system.

    Scoring categories:
        Tool use signals (max 35 pts):
            tier_a_imports * 5, capped at 15
            tier_b_imports * 3, capped at 9
            tier_c_imports * 5, capped at 11
        Production maturity signals (max 30 pts):
            production_keyword_score capped at 10
            repo_structure_score capped at 12
            repo_age_days >= 30: +3; >= 90: +2 more
            has_readme and readme_length > 500: +3
        Social proof / scale signals (max 20 pts):
            repo_stars: >=5 +2, >=25 +3, >=100 +3, >=500 +2
            contributor_count: >=2 +3, >=5 +3, >=10 +2
        Developer profile signals (max 15 pts):
            has_org: +5
            commit_count_30d: >=5 +2, >=15 +3, >=30 +2
            user_followers: >=10 +1, >=50 +1, >=200 +1

    Returns 0 immediately if lead_data['is_tutorial'] is True.
    Final score is capped at 100.

    Args:
        lead_data: Dict with keys: is_tutorial, tier_a_imports, tier_b_imports,
                   tier_c_imports, production_keyword_score, repo_structure_score,
                   repo_age_days, has_readme, readme_length, repo_stars,
                   contributor_count, has_org, commit_count_30d, user_followers

    Returns:
        Integer score 0-100.
    """
    pass


def infer_pain_point(lead_data: dict) -> str:
    """
    Determine the primary pain point string based on detected code patterns.

    Priority order (first match wins):
        1. "financial_risk"     — stripe/plaid/square/paypal in risk_apis, or "financial" in tool_categories
        2. "data_mutation_risk" — boto3/sqlalchemy/psycopg2/pymongo in risk_apis, or "database" in tool_categories
        3. "communication_risk" — twilio/sendgrid/slack_sdk in risk_apis, or "communication" in tool_categories
        4. "governance_at_scale"— contributor_count >= 3 AND framework in [langgraph, crewai, autogen]
        5. "blind_tool_calls"   — default fallback

    Args:
        lead_data: Dict with keys: risk_apis_detected (list), tool_categories (list),
                   framework (str), contributor_count (int)

    Returns:
        One of: "financial_risk", "data_mutation_risk", "communication_risk",
                "governance_at_scale", "blind_tool_calls"
    """
    pass
