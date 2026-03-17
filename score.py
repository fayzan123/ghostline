"""
score.py — Lead scoring, tier assignment, and pain point inference for the
Ghostline lead generation tool.
"""

import logging

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

logger = logging.getLogger(__name__)


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
    scored = []

    for lead in leads:
        lead_data = _build_lead_data(lead)

        score = score_lead(lead_data)
        lead.lead_score = score

        if score >= TIER1_THRESHOLD:
            lead.lead_tier = "tier_1"
        elif score >= TIER2_THRESHOLD:
            lead.lead_tier = "tier_2"
        else:
            # Below threshold — skip this lead
            logger.debug(
                "Lead %s scored %d (below tier2 threshold %d), dropping.",
                lead.github_username, score, TIER2_THRESHOLD,
            )
            continue

        lead.inferred_pain_point = infer_pain_point(lead_data)
        scored.append(lead)

    logger.info(
        "Scoring complete: %d/%d leads qualified (tier1=%d, tier2=%d).",
        len(scored),
        len(leads),
        sum(1 for l in scored if l.lead_tier == "tier_1"),
        sum(1 for l in scored if l.lead_tier == "tier_2"),
    )

    return scored


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
    if lead_data.get("is_tutorial", False):
        return 0

    score = 0

    # TOOL USE SIGNALS (max 35 pts)
    score += min(lead_data.get("tier_a_imports", 0) * 5, 15)
    score += min(lead_data.get("tier_b_imports", 0) * 3, 9)
    score += min(lead_data.get("tier_c_imports", 0) * 5, 11)

    # PRODUCTION MATURITY SIGNALS (max 30 pts)
    score += min(lead_data.get("production_keyword_score", 0), 10)
    score += min(lead_data.get("repo_structure_score", 0), 12)

    repo_age_days = lead_data.get("repo_age_days", 0)
    if repo_age_days >= 30:
        score += 3
    if repo_age_days >= 90:
        score += 2

    if lead_data.get("has_readme", False) and lead_data.get("readme_length", 0) > 500:
        score += 3

    # SOCIAL PROOF / SCALE SIGNALS (max 20 pts)
    repo_stars = lead_data.get("repo_stars", 0)
    if repo_stars >= 5:
        score += 2
    if repo_stars >= 25:
        score += 3
    if repo_stars >= 100:
        score += 3
    if repo_stars >= 500:
        score += 2

    contributor_count = lead_data.get("contributor_count", 0)
    if contributor_count >= 2:
        score += 3
    if contributor_count >= 5:
        score += 3
    if contributor_count >= 10:
        score += 2

    # DEVELOPER PROFILE SIGNALS (max 15 pts)
    if lead_data.get("has_org", False):
        score += 5

    commit_count_30d = lead_data.get("commit_count_30d", 0)
    if commit_count_30d >= 5:
        score += 2
    if commit_count_30d >= 15:
        score += 3
    if commit_count_30d >= 30:
        score += 2

    user_followers = lead_data.get("user_followers", 0)
    if user_followers >= 10:
        score += 1
    if user_followers >= 50:
        score += 1
    if user_followers >= 200:
        score += 1

    return min(score, 100)


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
    risk_apis = lead_data.get("risk_apis_detected", [])
    tool_categories = lead_data.get("tool_categories", [])

    # Build categories from risk_apis using IMPORT_TO_CATEGORY
    categories_from_apis = set()
    for api in risk_apis:
        for key, category in IMPORT_TO_CATEGORY.items():
            if key.lower() in api.lower():
                categories_from_apis.add(category)

    all_categories = set(tool_categories) | categories_from_apis

    # Priority 1: financial_risk
    if "financial" in all_categories:
        return "financial_risk"

    # Priority 2: data_mutation_risk
    if "database" in all_categories:
        return "data_mutation_risk"

    # Priority 3: communication_risk
    if "communication" in all_categories:
        return "communication_risk"

    # Priority 4: governance_at_scale
    contributor_count = lead_data.get("contributor_count", 1)
    framework = lead_data.get("framework", "").lower()
    if contributor_count >= 3 and framework in ("langgraph", "crewai", "autogen"):
        return "governance_at_scale"

    # Priority 5: default fallback
    return "blind_tool_calls"


def _build_lead_data(lead: Lead) -> dict:
    """
    Convert a Lead dataclass into the lead_data dict expected by score_lead()
    and infer_pain_point().

    Since we don't have full code analysis results on the Lead, we derive
    approximate signals from the available metadata fields.
    """
    frameworks = [f.strip().lower() for f in lead.frameworks_detected.split(",") if f.strip()]
    risk_apis = [r.strip() for r in lead.risk_apis_detected.split(",") if r.strip()]

    # Estimate import tier counts from frameworks_detected
    tier_a = 0
    tier_b = 0

    if "langgraph" in frameworks:
        # LangGraph implies tool use (tier_a) + state graph (tier_b)
        tier_a += 1
        tier_b += 1
    if "langchain" in frameworks:
        # LangChain implies at least basic tool use
        tier_a += 1

    # Tier C: count risk APIs detected
    tier_c = len(risk_apis)

    # Calculate production keyword score from repo description
    production_keyword_score = 0
    desc_lower = (lead.repo_description or "").lower()
    bio_lower = (lead.profile_bio or "").lower()
    searchable_text = f"{desc_lower} {bio_lower}"

    for kw in PRODUCTION_KEYWORDS:
        if kw in searchable_text:
            production_keyword_score += 2
    for kw in MODERATE_KEYWORDS:
        if kw in searchable_text:
            production_keyword_score += 1

    # Derive tool categories from risk_apis for pain point inference
    tool_categories = []
    for api in risk_apis:
        for key, category in IMPORT_TO_CATEGORY.items():
            if key.lower() in api.lower() and category not in tool_categories:
                tool_categories.append(category)

    # Pick the primary framework for pain point inference
    framework = ""
    if "langgraph" in frameworks:
        framework = "langgraph"
    elif "crewai" in frameworks:
        framework = "crewai"
    elif "autogen" in frameworks:
        framework = "autogen"
    elif "langchain" in frameworks:
        framework = "langchain"

    return {
        "is_tutorial": False,  # qualify.py already filtered tutorials
        "tier_a_imports": tier_a,
        "tier_b_imports": tier_b,
        "tier_c_imports": tier_c,
        "production_keyword_score": production_keyword_score,
        "repo_structure_score": 0,  # Would need API call to check file tree
        "repo_age_days": 30,  # Repos were pushed in last 30 days per discovery queries
        "has_readme": True,  # Most repos have READMEs
        "readme_length": 600,  # Assume substantive (can't check without API call)
        "repo_stars": lead.repo_stars,
        "contributor_count": 1,  # Would need API call to determine
        "has_org": bool(lead.profile_company),
        "commit_count_30d": 5,  # We know they committed recently from discovery
        "user_followers": lead.followers,
        "risk_apis_detected": risk_apis,
        "tool_categories": tool_categories,
        "framework": framework,
    }


if __name__ == "__main__":
    # --- Test score_lead ---
    print("=== score_lead() test ===\n")

    test_lead_data = {
        "is_tutorial": False,
        "tier_a_imports": 2,
        "tier_b_imports": 1,
        "tier_c_imports": 1,
        "production_keyword_score": 6,
        "repo_structure_score": 4,
        "repo_age_days": 45,
        "has_readme": True,
        "readme_length": 800,
        "repo_stars": 30,
        "contributor_count": 3,
        "has_org": True,
        "commit_count_30d": 20,
        "user_followers": 75,
    }

    score = score_lead(test_lead_data)
    if score >= TIER1_THRESHOLD:
        tier = "tier_1"
    elif score >= TIER2_THRESHOLD:
        tier = "tier_2"
    else:
        tier = "disqualified"

    print(f"  Score: {score}")
    print(f"  Tier:  {tier}")
    print(f"  (TIER1_THRESHOLD={TIER1_THRESHOLD}, TIER2_THRESHOLD={TIER2_THRESHOLD})")
    print()

    # Breakdown
    print("  Score breakdown:")
    print(f"    Tool use:    tier_a(2*5=10, cap 15) + tier_b(1*3=3, cap 9) + tier_c(1*5=5, cap 11) = 18")
    print(f"    Production:  kw(6, cap 10) + struct(4, cap 12) + age30(3) + readme(3) = 16")
    print(f"    Social:      stars>=25(+5) + contrib>=2(+3) = 8")
    print(f"    Profile:     org(+5) + commits>=15(+5) + followers>=50(+2) = 12")
    print(f"    Expected total: 18 + 16 + 8 + 12 = 54")
    print()

    # --- Test infer_pain_point ---
    print("=== infer_pain_point() tests ===\n")

    # Test financial risk
    pain_data_financial = {
        "risk_apis_detected": ["stripe"],
        "tool_categories": [],
        "framework": "langchain",
        "contributor_count": 1,
    }
    print(f"  Financial APIs (stripe):    {infer_pain_point(pain_data_financial)}")

    # Test database risk
    pain_data_db = {
        "risk_apis_detected": ["sqlalchemy"],
        "tool_categories": [],
        "framework": "langchain",
        "contributor_count": 1,
    }
    print(f"  Database APIs (sqlalchemy):  {infer_pain_point(pain_data_db)}")

    # Test communication risk
    pain_data_comm = {
        "risk_apis_detected": ["twilio"],
        "tool_categories": [],
        "framework": "langgraph",
        "contributor_count": 1,
    }
    print(f"  Comms APIs (twilio):         {infer_pain_point(pain_data_comm)}")

    # Test governance at scale
    pain_data_gov = {
        "risk_apis_detected": [],
        "tool_categories": [],
        "framework": "langgraph",
        "contributor_count": 5,
    }
    print(f"  Governance (langgraph, 5c):  {infer_pain_point(pain_data_gov)}")

    # Test default fallback
    pain_data_default = {
        "risk_apis_detected": [],
        "tool_categories": [],
        "framework": "langchain",
        "contributor_count": 1,
    }
    print(f"  Default (no signals):        {infer_pain_point(pain_data_default)}")

    # --- Test score_leads with a mock Lead ---
    print("\n=== score_leads() integration test ===\n")

    mock_lead = Lead(
        github_username="testdev",
        email="test@example.org",
        full_name="Test Developer",
        repo_url="https://github.com/testdev/my-agent",
        repo_name="testdev/my-agent",
        repo_description="Production AI agent workflow with langchain orchestration and deployment",
        repo_stars=50,
        repo_language="Python",
        frameworks_detected="langchain, langgraph",
        profile_bio="Building autonomous AI agents at scale",
        profile_company="Acme Corp",
        followers=120,
        public_repos=30,
        risk_apis_detected="stripe, boto3",
    )

    results = score_leads([mock_lead])
    if results:
        lead = results[0]
        print(f"  Username:    {lead.github_username}")
        print(f"  Score:       {lead.lead_score}")
        print(f"  Tier:        {lead.lead_tier}")
        print(f"  Pain Point:  {lead.inferred_pain_point}")
    else:
        print("  Lead was filtered out (score below threshold).")
