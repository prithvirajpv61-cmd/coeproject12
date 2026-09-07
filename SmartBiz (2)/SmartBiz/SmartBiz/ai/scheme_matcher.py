"""
SmartBiz scheme matching engine.

This is a transparent, rule-based scoring model (not a black-box ML model),
which is the right level of "AI" for a beginner project: it is explainable,
debuggable, and doesn't need an external API key or GPU. Each scheme gets a
0-100 match score against the user's submitted business details.
"""


def _normalize(text):
    return (text or "").strip().lower()


def score_scheme(scheme, user_input):
    """Return (score:int 0-100, reasons:list[str]) for one scheme."""
    score = 0
    max_score = 0
    reasons = []

    business_type = _normalize(user_input.get("business_type"))
    location = _normalize(user_input.get("location"))
    turnover = user_input.get("annual_turnover") or 0
    loan_amount = user_input.get("loan_amount") or 0
    purpose = _normalize(user_input.get("loan_purpose"))
    business_age = user_input.get("business_age")
    if business_age is None:
        business_age = 0

    # 1. Business type match — weight 30
    max_score += 30
    scheme_types = scheme.get("business_types", [])
    if any(bt in business_type or business_type in bt for bt in scheme_types):
        score += 30
        reasons.append("Business type matches this scheme's target sector")
    elif "all" in scheme_types:
        score += 15

    # 2. Location match — weight 15
    max_score += 15
    scheme_states = scheme.get("states", ["all"])
    if "all" in scheme_states:
        score += 15
    elif any(s in location for s in scheme_states):
        score += 15
        reasons.append("Scheme is specific to your state, improving relevance")

    # 3. Loan amount fits scheme's range — weight 25
    max_score += 25
    lo, hi = scheme.get("min_loan", 0), scheme.get("max_loan", 10**9)
    if lo <= loan_amount <= hi:
        score += 25
        reasons.append("Requested loan amount fits within this scheme's funding range")
    elif loan_amount < lo:
        score += 10  # scheme could still offer more than needed
    else:
        score += 0

    # 4. Turnover within scheme's expected band — weight 10
    max_score += 10
    t_lo, t_hi = scheme.get("min_turnover", 0), scheme.get("max_turnover", 10**9)
    if t_lo <= turnover <= t_hi:
        score += 10

    # 5. Purpose match — weight 15
    max_score += 15
    scheme_purposes = scheme.get("purposes", [])
    if any(p in purpose or purpose in p for p in scheme_purposes):
        score += 15
        reasons.append("Stated loan purpose aligns with what this scheme funds")
    else:
        score += 5

    # 6. New-unit-only restriction — weight 5 (can disqualify)
    max_score += 5
    if scheme.get("new_unit_only"):
        if business_age <= 1:
            score += 5
            reasons.append("Scheme is for new businesses and yours qualifies as new")
        else:
            score -= 15  # penalty: likely not eligible
            reasons.append("Scheme is limited to new/greenfield units; existing businesses may not qualify")
    else:
        score += 5

    pct = max(0, min(100, round((score / max_score) * 100))) if max_score else 0
    return pct, reasons


def match_schemes(all_schemes, user_input, top_n=None):
    """Score every scheme, sort by match desc, and return the ranked list."""
    results = []
    for scheme in all_schemes:
        pct, reasons = score_scheme(scheme, user_input)
        results.append({**scheme, "match_score": pct, "match_reasons": reasons})
    results.sort(key=lambda s: s["match_score"], reverse=True)
    if top_n:
        results = results[:top_n]
    return results


def explain_simple(scheme):
    """Very short plain-language explanation of a scheme (rule-based, not an LLM call)."""
    return (
        f"{scheme['scheme_name']} is meant for {', '.join(scheme.get('business_types', ['a range of'])[:3])} "
        f"businesses. In short: {scheme['description'].strip()} "
        f"Typical support ranges from the scheme's own stated loan/subsidy limits — "
        f"always check the official link before relying on this for a decision."
    )
