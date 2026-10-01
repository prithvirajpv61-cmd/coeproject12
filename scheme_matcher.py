"""
SmartBiz scheme matching engine.

This is a transparent, explainable, rule-based & fuzzy matching scoring model.
It extends rule-based scoring with semantic business-category taxonomy mapping,
fuzzy string comparison (difflib), multi-category tokenization, and comprehensive
edge-case handling (spelling typos, missing fields, extreme loan amounts, unknown categories).

Each scheme receives a 0-100 match score with detailed factor-by-factor explanations:
- Business Category Match
- Location Match
- Loan Amount Match
- Business Age Match
- Loan Purpose Match
- Turnover Match
"""

import re
import difflib
from typing import Dict, List, Tuple, Any, Optional, Set


# ---------------------------------------------------------------------------
# Business Category Taxonomy & Synonym Dictionary
# ---------------------------------------------------------------------------

# Canonical category mapping for Indian small businesses & MSME sectors
BUSINESS_TAXONOMY: Dict[str, Set[str]] = {
    "printing": {
        "xerox", "photocopy", "xerox shop", "photocopy shop", "printing", "offset printing",
        "digital printing", "printing press", "document services", "document center", "dtp",
        "desktop publishing", "binding", "book binding", "lamination", "stationery",
        "stationery shop", "screen printing", "flex printing", "banner printing",
        "publishing", "typing center", "scanning center", "graphic design studio"
    },
    "bakery": {
        "bakery", "bakeries", "bakehouse", "cake shop", "pastry shop", "confectionery",
        "confectionary", "biscuit making", "bread making", "patisserie", "sweet bakery"
    },
    "food": {
        "food", "food business", "food processing", "catering", "caterer", "restaurant",
        "hotel", "dhaba", "cafe", "coffee shop", "tea stall", "juice shop", "juice bar",
        "sweets shop", "sweet stall", "mithai shop", "snack manufacturing", "namkeen making",
        "fast food", "cloud kitchen", "mess", "canteen", "canteen service", "flour mill",
        "atta chakki", "spice grinding", "masala unit", "dairy", "dairy farm", "milk parlour",
        "milk booth", "ice cream parlour", "pickles", "papad making", "oil mill", "food packaging"
    },
    "retail": {
        "retail", "retail shop", "retail store", "grocery", "grocery shop", "grocery store",
        "kirana", "kirana store", "kirana shop", "provision store", "general store",
        "supermarket", "mini mart", "departmental store", "merchant", "trading", "retail trade",
        "cloth store", "cloth shop", "textile showroom", "footwear shop", "shoe store",
        "fancy store", "gift shop", "hardware store", "paints shop", "electrical goods shop",
        "sanitaryware shop", "stationery retail", "medical store", "pharmacy", "chemist",
        "vegetable shop", "fruit stall", "meat shop", "fish stall", "dealer", "distributor",
        "mobile shop", "mobile store", "smartphone shop", "electronics shop", "electronics retail"
    },
    "tailoring": {
        "tailoring", "tailor", "tailors", "tailoring shop", "garment", "garments",
        "garment manufacturing", "textile", "textiles", "apparel", "apparel making",
        "boutique", "ladies boutique", "dressmaking", "dressmaker", "embroidery",
        "aari work", "zari work", "sewing", "stitching", "sewing center", "fashion designing",
        "weaving", "powerloom", "handloom", "knitting", "readymade garments", "cloth stitching"
    },
    "workshop": {
        "workshop", "repair", "auto repair", "automobile service", "automobile repair",
        "mechanic", "garage", "car service", "car repair", "two wheeler repair",
        "bike service", "bike mechanic", "two wheeler service", "two wheeler workshop",
        "tyre shop", "puncture shop", "wheel alignment", "welding", "welding works",
        "fabrication", "metal fabrication", "lathe works", "machine shop", "carpentry",
        "furniture making", "wood working", "electrical repair", "motor rewinding",
        "appliance repair", "ac repair", "ac service", "refrigerator repair", "plumbing works"
    },
    "service": {
        "service", "services", "service enterprise", "service business", "salon", "beauty salon",
        "beauty parlour", "hair salon", "hair dressing", "barber shop", "spa", "cosmetics",
        "makeup studio", "laundry", "dry cleaners", "ironing shop", "car wash", "water wash",
        "courier service", "logistics", "transport service", "travel agency", "tour operator",
        "photography", "photo studio", "videography", "event management", "security agency",
        "cleaning service", "pest control", "coaching center", "tuition center", "training institute",
        "consultancy", "accounting service", "mobile repair", "smartphone service", "laptop service",
        "computer service", "it services", "repair center", "fitness gym", "yoga center"
    },
    "trading": {
        "trading", "trader", "traders", "wholesale", "wholesaler", "wholesale trade",
        "distribution", "distributor", "stockist", "dealer", "supplier", "reseller",
        "street vendor", "street vending", "hawker", "push cart vendor", "marketplace seller"
    },
    "manufacturing": {
        "manufacturing", "manufacturer", "production", "making", "fabrication", "factory",
        "small manufacturing unit", "processing unit", "industrial unit", "assembly",
        "plastic moulding", "paper products", "packaging unit", "chemical unit",
        "handicrafts", "artisan", "pottery", "leather products", "footwear making",
        "furniture manufacturing", "brick kiln", "cement products", "soap making", "candle making"
    }
}

# Stop words to ignore during normalization
STOP_WORDS = {
    "shop", "store", "center", "centre", "works", "unit", "business", "services",
    "service", "enterprise", "enterprises", "point", "corner", "hub", "pvt", "ltd",
    "co", "and", "&", "the", "a", "an", "of", "for", "in", "with"
}

# Common word stem/plural mappings
PLURAL_MAP = {
    "bakeries": "bakery",
    "salons": "salon",
    "parlours": "parlour",
    "parlors": "parlour",
    "repairs": "repair",
    "services": "service",
    "shops": "shop",
    "stores": "store",
    "garments": "garment",
    "textiles": "textile",
    "tailors": "tailor",
    "mechanics": "mechanic",
    "groceries": "grocery",
    "traders": "trading",
    "manufacturers": "manufacturing",
    "photocopies": "photocopy",
    "printers": "printing",
    "mills": "mill",
    "foods": "food"
}


# ---------------------------------------------------------------------------
# Text Normalization & Tokenization Helpers
# ---------------------------------------------------------------------------

def normalize_text(text: Any) -> str:
    """Normalize input text: lowercase, strip punctuation and extra whitespace."""
    if text is None:
        return ""
    text_str = str(text).lower().strip()
    # Replace non-alphanumeric characters (except spaces) with space
    text_str = re.sub(r"[^\w\s]", " ", text_str)
    # Collapse multiple spaces
    text_str = re.sub(r"\s+", " ", text_str).strip()
    return text_str


def tokenize_and_stem(text: str) -> List[str]:
    """Tokenize normalized text, remove stop words, and apply singular stem rules."""
    norm = normalize_text(text)
    if not norm:
        return []
    raw_tokens = norm.split()
    tokens = []
    for tok in raw_tokens:
        tok_stem = PLURAL_MAP.get(tok, tok)
        tokens.append(tok_stem)
    return tokens


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords excluding general stop words."""
    tokens = tokenize_and_stem(text)
    meaningful = [t for t in tokens if t not in STOP_WORDS]
    return meaningful if meaningful else tokens


# ---------------------------------------------------------------------------
# Fuzzy Business Category Matcher
# ---------------------------------------------------------------------------

def compute_string_similarity(str1: str, str2: str) -> float:
    """Calculate SequenceMatcher similarity between two strings."""
    s1, s2 = normalize_text(str1), normalize_text(str2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    if s1 in s2 or s2 in s1:
        return 0.9
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def find_taxonomy_categories(user_input_category: str) -> Dict[str, float]:
    """
    Map user input to canonical taxonomy sectors with matching confidence scores (0.0 to 1.0).
    Handles exact matches, synonyms, partial token containment, and fuzzy spelling.
    """
    norm_input = normalize_text(user_input_category)
    if not norm_input:
        return {}

    input_tokens = tokenize_and_stem(norm_input)
    input_keywords = extract_keywords(norm_input)

    matched_categories: Dict[str, float] = {}

    for canonical_cat, term_set in BUSINESS_TAXONOMY.items():
        best_score = 0.0

        # 1. Direct canonical name match or containment
        if norm_input == canonical_cat:
            best_score = max(best_score, 1.0)
        elif canonical_cat in norm_input or norm_input in canonical_cat:
            best_score = max(best_score, 0.95)

        # 2. Check full term in synonym dictionary
        if norm_input in term_set:
            best_score = max(best_score, 1.0)

        # 3. Check individual keywords / tokens against term set
        for term in term_set:
            term_norm = normalize_text(term)
            term_tokens = tokenize_and_stem(term_norm)

            # Direct substring match
            if norm_input in term_norm or term_norm in norm_input:
                best_score = max(best_score, 0.92)

            # Keyword containment
            for kw in input_keywords:
                if kw in term_tokens or kw in term_norm:
                    best_score = max(best_score, 0.88)
                else:
                    # Fuzzy match on individual words (handles typos like 'bakkery', 'printting', 'tailering')
                    for tt in term_tokens:
                        sim = difflib.SequenceMatcher(None, kw, tt).ratio()
                        if sim >= 0.82:
                            best_score = max(best_score, sim * 0.9)

        if best_score > 0.4:
            matched_categories[canonical_cat] = round(best_score, 2)

    return matched_categories


def match_business_category(user_category: str, scheme_categories: List[str]) -> Tuple[float, str, str]:
    """
    Compare user's business type with the scheme's allowed business types.
    Returns:
        (category_similarity: float 0.0-1.0, match_status: str, match_detail: str)
    """
    user_norm = normalize_text(user_category)
    scheme_cats = [normalize_text(sc) for sc in (scheme_categories or [])]

    # Edge Case 1: Empty user input
    if not user_norm:
        return (
            0.5,
            "General match",
            "No specific business category entered; scheme evaluated for broad eligibility."
        )

    # Edge Case 2: Scheme accepts "all" or general micro-enterprises
    if "all" in scheme_cats or not scheme_cats:
        return (
            0.85,
            "Broad sector match",
            f"Scheme applies to all general MSME business types including '{user_category}'."
        )

    # Direct match check
    for sc in scheme_cats:
        if user_norm == sc:
            return (
                1.0,
                "Exact category match",
                f"Your business category '{user_category}' exactly matches the scheme's target sector ({sc.title()})."
            )
        if user_norm in sc or sc in user_norm:
            return (
                0.95,
                "Strong direct match",
                f"Your business category '{user_category}' directly aligns with the scheme's '{sc.title()}' category."
            )

    # Taxonomy & Synonym Resolution
    taxonomy_matches = find_taxonomy_categories(user_category)

    best_sim = 0.0
    best_scheme_cat = ""
    best_reason = ""

    for sc in scheme_cats:
        # If the scheme category is in taxonomy matches
        if sc in taxonomy_matches:
            score = taxonomy_matches[sc]
            if score > best_sim:
                best_sim = score
                best_scheme_cat = sc
                best_reason = (
                    f"Your business '{user_category}' is classified under '{sc.title()}' "
                    f"(confidence: {int(score * 100)}%), which is officially funded by this scheme."
                )

        # Also fuzzy match scheme category string directly against user input
        fuzzy_score = compute_string_similarity(user_norm, sc)
        if fuzzy_score > best_sim:
            best_sim = fuzzy_score
            best_scheme_cat = sc
            best_reason = (
                f"Your business '{user_category}' closely matches '{sc.title()}' "
                f"(similarity: {int(fuzzy_score * 100)}%)."
            )

    # Broader service/manufacturing fallback:
    # If user has a service-type business and scheme accepts "service"
    if best_sim < 0.6:
        service_terms = {"salon", "mechanic", "repair", "laundry", "studio", "consulting", "courier", "cleaning", "clinic"}
        mfg_terms = {"making", "manufacturing", "production", "fabrication", "mill", "processing", "craft"}
        user_kw = extract_keywords(user_norm)

        if "service" in scheme_cats and any(t in user_norm or t in user_kw for t in service_terms):
            best_sim = 0.85
            best_reason = f"Your business '{user_category}' operates as a service enterprise, covered by this scheme's Service category."
        elif "manufacturing" in scheme_cats and any(t in user_norm or t in user_kw for t in mfg_terms):
            best_sim = 0.85
            best_reason = f"Your business '{user_category}' involves production/processing, covered by this scheme's Manufacturing category."
        elif "retail" in scheme_cats and any(t in user_norm for t in ["shop", "store", "mart", "trading", "retail"]):
            best_sim = 0.80
            best_reason = f"Your business '{user_category}' operates in trading/retail, matching this scheme's Retail sector."

    if best_sim >= 0.85:
        return (best_sim, "Strong match", best_reason)
    elif best_sim >= 0.65:
        return (best_sim, "Moderate match", best_reason or f"Business category '{user_category}' partially aligns with scheme's target sectors.")
    elif best_sim >= 0.40:
        return (best_sim, "Partial match", f"Business category '{user_category}' has partial overlap with scheme's sector ({', '.join(scheme_cats)}).")
    else:
        # Edge Case 3: Unknown or non-matching category
        return (
            0.15,
            "Low category overlap",
            f"Business category '{user_category}' is outside the scheme's primary sectors ({', '.join(scheme_cats[:3])})."
        )


# ---------------------------------------------------------------------------
# Comprehensive Scheme Scoring Engine
# ---------------------------------------------------------------------------

def score_scheme(scheme: Dict[str, Any], user_input: Dict[str, Any]) -> Tuple[int, List[str], Dict[str, Any]]:
    """
    Score a single scheme against user inputs.
    Returns:
        (pct_score: int (0-100), reasons: List[str], factors_breakdown: Dict[str, Any])
    """
    score = 0.0
    max_score = 0.0
    reasons: List[str] = []
    factors: Dict[str, Any] = {}

    # Extract user inputs safely with robust defaults
    business_type_raw = user_input.get("business_type", "")
    business_type = normalize_text(business_type_raw)
    location_raw = user_input.get("location", "")
    location = normalize_text(location_raw)

    turnover = user_input.get("annual_turnover")
    turnover = int(turnover) if isinstance(turnover, (int, float)) and turnover >= 0 else 0

    loan_amount = user_input.get("loan_amount")
    loan_amount = int(loan_amount) if isinstance(loan_amount, (int, float)) and loan_amount >= 0 else 0

    purpose_raw = user_input.get("loan_purpose", "")
    purpose = normalize_text(purpose_raw)

    business_age = user_input.get("business_age")
    try:
        business_age = int(business_age) if business_age is not None else 0
        business_age = max(0, business_age)
    except (ValueError, TypeError):
        business_age = 0

    # -----------------------------------------------------------------------
    # 1. Business Category Match (Weight: 35 points)
    # -----------------------------------------------------------------------
    max_score += 35.0
    scheme_types = scheme.get("business_types", ["all"])
    cat_similarity, cat_status, cat_detail = match_business_category(business_type_raw, scheme_types)
    cat_points = round(cat_similarity * 35.0, 1)
    score += cat_points

    factors["business_category"] = {
        "title": "Business Category",
        "score_earned": cat_points,
        "max_score": 35,
        "status": cat_status,
        "detail": cat_detail,
        "similarity_pct": int(cat_similarity * 100),
        "is_positive": cat_similarity >= 0.7
    }
    if cat_similarity >= 0.75:
        reasons.append(cat_detail)
    elif cat_similarity < 0.4 and business_type_raw:
        reasons.append(f"Business category '{business_type_raw}' may require verification for this scheme.")

    # -----------------------------------------------------------------------
    # 2. Location Match (Weight: 15 points)
    # -----------------------------------------------------------------------
    max_score += 15.0
    scheme_states = [normalize_text(s) for s in scheme.get("states", ["all"])]

    if "all" in scheme_states or not scheme_states:
        loc_score = 15.0
        loc_status = "All-India scheme"
        loc_detail = "This is a Central government scheme valid across all Indian States & Union Territories."
        score += loc_score
        reasons.append("All-India eligibility: accessible regardless of state.")
    elif location and any(s in location or location in s for s in scheme_states):
        loc_score = 15.0
        loc_status = "State match"
        matching_state = next(s for s in scheme_states if s in location or location in s)
        loc_detail = f"Scheme is specifically tailored for {matching_state.title()}, matching your location ({location_raw})."
        score += loc_score
        reasons.append(f"State-specific match: scheme is active in {location_raw}.")
    elif not location:
        loc_score = 10.0
        loc_status = "Location optional"
        loc_detail = f"Scheme restricted to {', '.join(scheme_states).title()}; no location specified."
        score += loc_score
    else:
        loc_score = 0.0
        loc_status = "State mismatch"
        loc_detail = f"Scheme is restricted to {', '.join(scheme_states).title()}, but your location is '{location_raw}'."
        score += loc_score
        reasons.append(f"Location restriction: only applicable in {', '.join(scheme_states).title()}.")

    factors["location"] = {
        "title": "Location Eligibility",
        "score_earned": loc_score,
        "max_score": 15,
        "status": loc_status,
        "detail": loc_detail,
        "is_positive": loc_score >= 12
    }

    # -----------------------------------------------------------------------
    # 3. Loan Amount Match (Weight: 25 points)
    # -----------------------------------------------------------------------
    max_score += 25.0
    min_loan = scheme.get("min_loan", 0)
    max_loan = scheme.get("max_loan", 10**9)

    if loan_amount == 0:
        loan_pts = 15.0
        loan_status = "Amount unspecified"
        loan_detail = f"Supports funding from ₹{min_loan:,} up to ₹{max_loan:,}."
        score += loan_pts
    elif min_loan <= loan_amount <= max_loan:
        loan_pts = 25.0
        loan_status = "Within supported range"
        loan_detail = f"Your required amount (₹{loan_amount:,}) fits comfortably inside scheme's limits (₹{min_loan:,} to ₹{max_loan:,})."
        score += loan_pts
        reasons.append(f"Funding match: requested ₹{loan_amount:,} is within scheme range.")
    elif loan_amount < min_loan:
        # User wants less than minimum
        ratio = loan_amount / max(1, min_loan)
        loan_pts = max(5.0, round(12.0 * ratio, 1))
        loan_status = "Below scheme minimum"
        loan_detail = f"Requested loan (₹{loan_amount:,}) is below the minimum threshold (₹{min_loan:,}). Scheme may offer higher funding than requested."
        score += loan_pts
    else:
        # User wants more than scheme ceiling
        overage_ratio = max_loan / max(1, loan_amount)
        if loan_amount > (max_loan * 1.5) or overage_ratio < 0.2:
            loan_pts = 0.0
        else:
            loan_pts = max(0.0, round(10.0 * overage_ratio, 1))
        loan_status = "Exceeds scheme maximum"
        loan_detail = f"Requested loan (₹{loan_amount:,}) exceeds the maximum cap of ₹{max_loan:,} for this scheme."
        score += loan_pts

    factors["loan_amount"] = {
        "title": "Loan Requirement",
        "score_earned": loan_pts,
        "max_score": 25,
        "status": loan_status,
        "detail": loan_detail,
        "is_positive": loan_pts >= 18
    }

    # -----------------------------------------------------------------------
    # 4. Turnover Match (Weight: 10 points)
    # -----------------------------------------------------------------------
    max_score += 10.0
    min_turnover = scheme.get("min_turnover", 0)
    max_turnover = scheme.get("max_turnover", 10**9)

    if min_turnover <= turnover <= max_turnover:
        t_pts = 10.0
        t_status = "Turnover eligible"
        t_detail = f"Your turnover (₹{turnover:,}) is within the scheme's eligible limit (up to ₹{max_turnover:,})."
        score += t_pts
    else:
        t_pts = 3.0
        t_status = "Turnover outside band"
        t_detail = f"Scheme typically targets businesses with turnover between ₹{min_turnover:,} and ₹{max_turnover:,}."
        score += t_pts

    factors["turnover"] = {
        "title": "Annual Turnover",
        "score_earned": t_pts,
        "max_score": 10,
        "status": t_status,
        "detail": t_detail,
        "is_positive": t_pts >= 8
    }

    # -----------------------------------------------------------------------
    # 5. Purpose Match (Weight: 10 points)
    # -----------------------------------------------------------------------
    max_score += 10.0
    scheme_purposes = [normalize_text(p) for p in scheme.get("purposes", [])]

    if not purpose or not scheme_purposes:
        p_pts = 7.0
        p_status = "General purpose"
        p_detail = "Supports standard business setups, working capital, and asset creation."
        score += p_pts
    elif any(p in purpose or purpose in p for p in scheme_purposes):
        p_pts = 10.0
        p_status = "Aligned purpose"
        p_detail = f"Your loan purpose ('{purpose_raw}') aligns directly with what this scheme finances."
        score += p_pts
        reasons.append("Purpose fit: stated loan use matches scheme mandate.")
    else:
        p_pts = 4.0
        p_status = "Broad purpose fit"
        p_detail = f"Scheme primarily finances {', '.join(scheme_purposes)}, but related uses may be considered."
        score += p_pts

    factors["purpose"] = {
        "title": "Loan Purpose",
        "score_earned": p_pts,
        "max_score": 10,
        "status": p_status,
        "detail": p_detail,
        "is_positive": p_pts >= 7
    }

    # -----------------------------------------------------------------------
    # 6. Business Age & New Unit Restriction (Weight: 5 points with penalty)
    # -----------------------------------------------------------------------
    max_score += 5.0
    new_unit_only = scheme.get("new_unit_only", False)

    if new_unit_only:
        if business_age <= 1:
            age_pts = 5.0
            age_status = "Meets new unit requirement"
            age_detail = "Scheme is designed for new/greenfield units; your business age (0–1 yr) qualifies."
            score += age_pts
            reasons.append("New unit qualification: your venture fits greenfield mandate.")
        else:
            age_pts = -15.0  # Significant penalty for existing business applying to greenfield-only scheme
            age_status = "Ineligible: Existing enterprise"
            age_detail = f"Scheme is strictly for NEW greenfield businesses; your business is {business_age} years old."
            score += age_pts
            reasons.append("Restricted to new ventures; existing operations may not qualify.")
    else:
        age_pts = 5.0
        age_status = "Open to new & existing"
        age_detail = f"Open to both new and existing enterprises ({business_age} yrs)."
        score += age_pts

    factors["business_age"] = {
        "title": "Business Age Fit",
        "score_earned": max(0, age_pts),
        "max_score": 5,
        "status": age_status,
        "detail": age_detail,
        "is_positive": age_pts >= 0
    }

    # -----------------------------------------------------------------------
    # Final Normalized Percentage Score Calculation
    # -----------------------------------------------------------------------
    pct = max(0, min(100, round((score / max_score) * 100))) if max_score > 0 else 0

    # Summary overall explanation
    if pct >= 80:
        summary_explanation = (
            f"High match ({pct}%) because your business category matches the scheme's target sector "
            f"and your loan requirement is within the supported funding range."
        )
    elif pct >= 60:
        summary_explanation = (
            f"Moderate match ({pct}%) with strong potential; some criteria such as sector overlap "
            f"or funding caps should be verified against official scheme guidelines."
        )
    else:
        summary_explanation = (
            f"Exploratory match ({pct}%); please review specific eligibility conditions "
            f"or state/category restrictions on the official portal."
        )

    factors["summary_explanation"] = summary_explanation
    factors["disclaimer"] = (
        "Match score is an informational recommendation and does not guarantee official eligibility. "
        "Please verify eligibility on the official scheme website."
    )

    return pct, reasons, factors


# ---------------------------------------------------------------------------
# Public Ranking and Explanation APIs
# ---------------------------------------------------------------------------

def match_schemes(all_schemes: List[Dict[str, Any]], user_input: Dict[str, Any], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Score every scheme, attach detailed factors and explanations, sort descending by match score.
    """
    results = []
    for scheme in all_schemes:
        pct, reasons, factors = score_scheme(scheme, user_input)
        scheme_copy = dict(scheme)
        scheme_copy["match_score"] = pct
        scheme_copy["match_reasons"] = reasons
        scheme_copy["match_factors"] = factors
        scheme_copy["summary_explanation"] = factors.get("summary_explanation", "")
        results.append(scheme_copy)

    results.sort(key=lambda s: s["match_score"], reverse=True)
    if top_n is not None and top_n > 0:
        results = results[:top_n]
    return results


def explain_simple(scheme: Dict[str, Any]) -> str:
    """Very short plain-language explanation of a scheme for quick reading."""
    types_list = scheme.get("business_types", ["various small business"])
    types_str = ", ".join(types_list[:3])
    desc = scheme.get("description", "").strip()
    return (
        f"{scheme.get('scheme_name', 'This scheme')} is intended for {types_str} enterprises. "
        f"In summary: {desc} Support ranges within the scheme's designated loan and subsidy limits. "
        f"Always verify terms on the official government website before applying."
    )
