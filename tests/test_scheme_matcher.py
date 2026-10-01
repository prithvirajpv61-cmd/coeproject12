"""
Unit and Integration Tests for SmartBiz Scheme Matching Engine.

Covers:
1. Exact category match
2. Similar category match (synonym taxonomy)
3. Spelling variations & typos
4. Partial category match / Multi-category inputs
5. Unknown business category (graceful fallback)
6. Empty or None category
7. Loan amount below scheme minimum
8. Loan amount above scheme maximum
9. Valid location (All-India vs State specific)
10. Non-matching location (State restriction penalty)
11. Business age constraints (New unit only vs Existing)
12. Crash resilience on unexpected/invalid types
"""

import unittest
from schemes_data import SCHEMES
from scheme_matcher import (
    score_scheme,
    match_schemes,
    match_business_category,
    normalize_text,
    find_taxonomy_categories,
    explain_simple
)


class TestSchemeMatcher(unittest.TestCase):

    def setUp(self):
        self.schemes = SCHEMES

    # -----------------------------------------------------------------------
    # 1. Exact Category Match
    # -----------------------------------------------------------------------
    def test_01_exact_category_match(self):
        """User input directly matches scheme's sector string."""
        user_input = {
            "business_type": "manufacturing",
            "location": "Tamil Nadu",
            "loan_amount": 1000000,
            "business_age": 0
        }
        results = match_schemes(self.schemes, user_input)
        top_scheme = results[0]

        self.assertGreaterEqual(top_scheme["match_score"], 80)
        self.assertIn("match_factors", top_scheme)
        self.assertEqual(
            top_scheme["match_factors"]["business_category"]["status"],
            "Exact category match"
        )
        self.assertIn("matches", top_scheme["match_factors"]["business_category"]["detail"].lower())

    # -----------------------------------------------------------------------
    # 2. Similar Category Match (Taxonomy Resolution)
    # -----------------------------------------------------------------------
    def test_02_similar_category_matches(self):
        """Fuzzy taxonomy maps colloquial business terms to official categories."""
        test_pairs = [
            ("Xerox Shop", "printing"),
            ("Bakery", "bakery"),
            ("Grocery Shop", "retail"),
            ("Tailoring", "tailoring"),
            ("Mobile Shop", "retail"),
            ("Salon", "service"),
            ("Auto Repair", "workshop")
        ]

        for user_term, expected_sector in test_pairs:
            sim, status, detail = match_business_category(user_term, [expected_sector, "manufacturing"])
            self.assertGreaterEqual(
                sim,
                0.80,
                f"Expected '{user_term}' to match '{expected_sector}' with >= 0.80 similarity, got {sim}"
            )
            self.assertIn(status, ["Exact category match", "Strong direct match", "Strong match"])

    # -----------------------------------------------------------------------
    # 3. Spelling Variations & Typos
    # -----------------------------------------------------------------------
    def test_03_spelling_variations(self):
        """Handles common spelling errors and typos without score collapse."""
        typo_cases = [
            ("bakkery", "bakery"),
            ("printting", "printing"),
            ("tailering", "tailoring"),
            ("groccery", "retail"),
            ("automoble repair", "workshop")
        ]

        for typo, target_cat in typo_cases:
            sim, status, detail = match_business_category(typo, [target_cat, "manufacturing"])
            self.assertGreaterEqual(
                sim,
                0.70,
                f"Typo '{typo}' failed to match target '{target_cat}' (sim={sim})"
            )

    # -----------------------------------------------------------------------
    # 4. Partial Category Match & Multi-Category Input
    # -----------------------------------------------------------------------
    def test_04_partial_and_multi_category_match(self):
        """Supports compound names like 'Mobile Sales and Repair' or 'Bakery & Sweets'."""
        user_input = {
            "business_type": "Mobile Sales and Repair Center",
            "location": "Karnataka",
            "loan_amount": 500000,
            "business_age": 2
        }
        results = match_schemes(self.schemes, user_input)
        top_scheme = results[0]
        # Should match MUDRA or CGTMSE (Retail / Service / Trading)
        self.assertGreaterEqual(top_scheme["match_score"], 70)

    # -----------------------------------------------------------------------
    # 5. Unknown Business Category (Graceful Fallback)
    # -----------------------------------------------------------------------
    def test_05_unknown_category(self):
        """Unknown or unusual business names do not crash and get baseline score."""
        user_input = {
            "business_type": "Interstellar Deep Space Rocket Launch Services",
            "location": "Delhi",
            "loan_amount": 500000,
            "business_age": 0
        }
        results = match_schemes(self.schemes, user_input)
        self.assertEqual(len(results), len(self.schemes))
        # Verify it didn't crash and returns valid percentage scores (0-100)
        for r in results:
            self.assertGreaterEqual(r["match_score"], 0)
            self.assertLessEqual(r["match_score"], 100)

    # -----------------------------------------------------------------------
    # 6. Empty / None Category
    # -----------------------------------------------------------------------
    def test_06_empty_category(self):
        """Empty string or None in business_type is handled gracefully."""
        empty_inputs = [
            {"business_type": "", "location": "Tamil Nadu", "loan_amount": 300000},
            {"business_type": None, "location": "Tamil Nadu", "loan_amount": 300000},
            {"business_type": "    ", "location": "Tamil Nadu", "loan_amount": 300000}
        ]

        for u_input in empty_inputs:
            results = match_schemes(self.schemes, u_input)
            self.assertEqual(len(results), len(self.schemes))
            self.assertGreaterEqual(results[0]["match_score"], 30)

    # -----------------------------------------------------------------------
    # 7. Loan Amount Below Scheme Minimum
    # -----------------------------------------------------------------------
    def test_07_loan_amount_below_minimum(self):
        """Stand-Up India has min_loan = 10,00,000; requesting ₹50,000 gets partial score."""
        standup_scheme = next(s for s in self.schemes if "Stand-Up" in s["scheme_name"])
        user_input = {
            "business_type": "manufacturing",
            "location": "Maharashtra",
            "loan_amount": 50000,
            "business_age": 0
        }
        pct, reasons, factors = score_scheme(standup_scheme, user_input)
        self.assertEqual(factors["loan_amount"]["status"], "Below scheme minimum")
        self.assertLess(factors["loan_amount"]["score_earned"], 25)

    # -----------------------------------------------------------------------
    # 8. Loan Amount Above Scheme Maximum
    # -----------------------------------------------------------------------
    def test_08_loan_amount_above_maximum(self):
        """PM SVANidhi has max_loan = 50,000; requesting ₹50,00,000 is flagged."""
        svanidhi = next(s for s in self.schemes if "SVANidhi" in s["scheme_name"])
        user_input = {
            "business_type": "retail",
            "location": "Delhi",
            "loan_amount": 5000000,
            "business_age": 1
        }
        pct, reasons, factors = score_scheme(svanidhi, user_input)
        self.assertEqual(factors["loan_amount"]["status"], "Exceeds scheme maximum")
        self.assertEqual(factors["loan_amount"]["score_earned"], 0.0)

    # -----------------------------------------------------------------------
    # 9. Valid Location (State Specific Match)
    # -----------------------------------------------------------------------
    def test_09_valid_location_state_match(self):
        """TN NEEDS scheme is specific to Tamil Nadu."""
        tn_needs = next(s for s in self.schemes if "NEEDS" in s["scheme_name"])
        user_input = {
            "business_type": "manufacturing",
            "location": "Tamil Nadu",
            "loan_amount": 1000000,
            "business_age": 0
        }
        pct, reasons, factors = score_scheme(tn_needs, user_input)
        self.assertEqual(factors["location"]["status"], "State match")
        self.assertEqual(factors["location"]["score_earned"], 15.0)

    # -----------------------------------------------------------------------
    # 10. Non-Matching Location (State Restriction)
    # -----------------------------------------------------------------------
    def test_10_non_matching_location(self):
        """TN NEEDS scheme evaluated for applicant in Gujarat yields State mismatch."""
        tn_needs = next(s for s in self.schemes if "NEEDS" in s["scheme_name"])
        user_input = {
            "business_type": "manufacturing",
            "location": "Gujarat",
            "loan_amount": 1000000,
            "business_age": 0
        }
        pct, reasons, factors = score_scheme(tn_needs, user_input)
        self.assertEqual(factors["location"]["status"], "State mismatch")
        self.assertEqual(factors["location"]["score_earned"], 0.0)

    # -----------------------------------------------------------------------
    # 11. Business Age & Greenfield Requirement
    # -----------------------------------------------------------------------
    def test_11_business_age_greenfield_penalty(self):
        """Existing 5-year old business gets penalty for greenfield-only PMEGP scheme."""
        pmegp = next(s for s in self.schemes if "PMEGP" in s["scheme_name"])
        # New unit (age 0)
        u_new = {"business_type": "bakery", "location": "Tamil Nadu", "loan_amount": 500000, "business_age": 0}
        score_new, _, factors_new = score_scheme(pmegp, u_new)
        self.assertEqual(factors_new["business_age"]["status"], "Meets new unit requirement")

        # Existing unit (age 5)
        u_old = {"business_type": "bakery", "location": "Tamil Nadu", "loan_amount": 500000, "business_age": 5}
        score_old, _, factors_old = score_scheme(pmegp, u_old)
        self.assertIn("Ineligible: Existing enterprise", factors_old["business_age"]["status"])
        self.assertGreater(score_new, score_old)

    # -----------------------------------------------------------------------
    # 12. Robustness to Extreme / Invalid Inputs
    # -----------------------------------------------------------------------
    def test_12_crash_resilience(self):
        """Ensures the matching engine never raises an uncaught exception on invalid data."""
        bad_inputs = [
            {},
            {"loan_amount": "invalid_number", "annual_turnover": None},
            {"business_age": -10, "loan_amount": -500000},
            {"business_type": 12345, "location": ["array", "not", "str"]},
            {"loan_amount": 10**12, "annual_turnover": 10**12}
        ]

        for b_in in bad_inputs:
            try:
                results = match_schemes(self.schemes, b_in)
                self.assertIsInstance(results, list)
            except Exception as e:
                self.fail(f"Matching engine crashed on bad input {b_in} with error: {e}")


if __name__ == "__main__":
    unittest.main()
