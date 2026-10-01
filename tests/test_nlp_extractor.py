"""
Unit and Integration Tests for NLP Eligibility Extractor.

Covers:
1. Sector and business type extraction with source sentence retention
2. Loan limits and project cost parsing (Rupees, Lakhs, Crores)
3. Age requirement and greenfield/new unit constraint parsing
4. Document checklist extraction
5. Status initialization to UNVERIFIED_DRAFT (safety rule)
6. Export prohibition without human verification
7. Human-in-the-Loop verification sign-off and audit metadata
"""

import unittest
from nlp_eligibility_extractor import (
    NLPEligibilityExtractor,
    SchemeExtractionResult,
    ExtractedField
)


class TestNLPEligibilityExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = NLPEligibilityExtractor()

        self.sample_pmegp_text = """
        Prime Minister's Employment Generation Programme (PMEGP) is a credit-linked subsidy scheme
        for setting up new micro-enterprises in manufacturing or service sectors.
        Eligible beneficiaries must be individuals above 18 years of age.
        The scheme is restricted to new projects only (not applicable to existing business units).
        Maximum project cost eligible for manufacturing units is Rs 50 lakh and for service units is Rs 20 lakh.
        Government subsidy is 15% to 35% of project cost depending on area and beneficiary category.
        Required documents include Aadhaar card, PAN card, educational certificate, detailed project report, and caste certificate.
        Official website: https://www.kviconline.gov.in/pmegpeportal/
        """

        self.sample_mudra_text = """
        Pradhan Mantri MUDRA Yojana offers collateral-free loans for non-farm micro and small enterprises
        engaged in trading, retail, manufacturing and service activities.
        Any Indian citizen aged between 18 and 65 years can apply for existing or new business setups.
        Loans are provided in three categories: Shishu up to Rs 50,000, Kishor up to Rs 5 lakh, and Tarun up to Rs 10 lakh.
        Documents required: Udyam registration, ID proof, address proof, and quotation of machinery.
        Official portal: https://www.mudra.org.in/
        """

    # -----------------------------------------------------------------------
    # 1. Sector and Business Type Extraction with Evidence
    # -----------------------------------------------------------------------
    def test_01_sector_extraction_with_evidence(self):
        """Extracts manufacturing and service sectors and retains verbatim sentence quote."""
        res = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP Circular")
        sectors = res.eligible_sectors.value
        self.assertIn("manufacturing", sectors)
        self.assertIn("service", sectors)
        self.assertTrue(len(res.eligible_sectors.evidence_quote) > 0)
        self.assertIn("manufacturing", res.eligible_sectors.evidence_quote.lower())

    # -----------------------------------------------------------------------
    # 2. Loan Limits and Currency Parsing
    # -----------------------------------------------------------------------
    def test_02_loan_limit_parsing(self):
        """Correctly converts 'Rs 50 lakh' to integer 5,000,000."""
        res_pmegp = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        self.assertEqual(res_pmegp.max_loan.value, 5000000)

        res_mudra = self.extractor.extract_from_text(self.sample_mudra_text, "MUDRA")
        self.assertEqual(res_mudra.max_loan.value, 1000000)

    # -----------------------------------------------------------------------
    # 3. Age Requirements and Greenfield Parsing
    # -----------------------------------------------------------------------
    def test_03_age_and_greenfield_rules(self):
        """Extracts minimum age (18) and greenfield status (True for PMEGP, False for MUDRA)."""
        res_pmegp = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        self.assertEqual(res_pmegp.min_age.value, 18)
        self.assertTrue(res_pmegp.new_unit_only.value)

        res_mudra = self.extractor.extract_from_text(self.sample_mudra_text, "MUDRA")
        self.assertEqual(res_mudra.min_age.value, 18)
        self.assertEqual(res_mudra.max_age.value, 65)
        self.assertFalse(res_mudra.new_unit_only.value)

    # -----------------------------------------------------------------------
    # 4. Required Document Extraction
    # -----------------------------------------------------------------------
    def test_04_document_extraction(self):
        """Identifies standard Indian KYC, DPR, Udyam, and Caste certificates."""
        res = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        docs = res.required_documents.value
        self.assertTrue(any("Identity Proof" in d for d in docs))
        self.assertTrue(any("Detailed Project Report" in d for d in docs))
        self.assertTrue(any("Community" in d or "Caste" in d for d in docs))

    # -----------------------------------------------------------------------
    # 5. Safety Status: UNVERIFIED_DRAFT by Default
    # -----------------------------------------------------------------------
    def test_05_unverified_draft_initialization(self):
        """All fresh extractions MUST be tagged as UNVERIFIED_DRAFT."""
        res = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        self.assertEqual(res.status, "UNVERIFIED_DRAFT")
        self.assertIsNone(res.verified_by)

    # -----------------------------------------------------------------------
    # 6. Export Prohibition for Unverified Data
    # -----------------------------------------------------------------------
    def test_06_unverified_export_blocked(self):
        """Attempting to export unverified scheme data raises PermissionError."""
        res = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        with self.assertRaises(PermissionError):
            self.extractor.export_to_scheme_data_format(res, enforce_verification=True)

    # -----------------------------------------------------------------------
    # 7. Human-in-the-Loop Verification Sign-off
    # -----------------------------------------------------------------------
    def test_07_human_verification_signoff(self):
        """Reviewer sign-off marks status as VERIFIED and records audit trail."""
        res = self.extractor.extract_from_text(self.sample_pmegp_text, "PMEGP")
        verified_res = self.extractor.verify_extraction(
            res,
            verifier_name="Dr. K. Ramanathan (Scheme Verification Officer)",
            notes="Cross-checked against MSME Gazette 2024 notification."
        )

        self.assertEqual(verified_res.status, "VERIFIED")
        self.assertEqual(verified_res.verified_by, "Dr. K. Ramanathan (Scheme Verification Officer)")
        self.assertIsNotNone(verified_res.verification_timestamp)

        # Now exporting to scheme catalog format must succeed
        scheme_dict = self.extractor.export_to_scheme_data_format(verified_res)
        self.assertIsInstance(scheme_dict, dict)
        self.assertEqual(scheme_dict["verification_audit"]["status"], "VERIFIED")
        self.assertEqual(scheme_dict["max_loan"], 5000000)


if __name__ == "__main__":
    unittest.main()
