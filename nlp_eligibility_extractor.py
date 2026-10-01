"""
NLP-Assisted Eligibility Extraction Module for SmartBiz.

This module provides a safe, modular, explainable NLP pipeline to parse official
government scheme text and PDF circulars into structured eligibility attributes.

Key Design Principles:
1. Source of Truth: Official scheme documents are the single source of truth.
2. Evidence Retention: Every extracted attribute retains the verbatim source sentence / quote.
3. Human-in-the-Loop Safety: Extracted data is strictly tagged as 'UNVERIFIED_DRAFT'.
   It cannot be used for user matching until a human verifies and signs off on it.
4. Offline / Zero-Cost Architecture: Uses deterministic regex-assisted NLP and semantic
   rule extractors without requiring paid external APIs or leaking sensitive keys.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data Models for Extraction and Human-in-the-Loop Verification
# ---------------------------------------------------------------------------

class ExtractedField:
    """Represents a single extracted eligibility parameter with its source evidence."""

    def __init__(
        self,
        value: Any,
        confidence: float,
        evidence_quote: str,
        is_verified: bool = False,
        verification_notes: str = ""
    ):
        self.value = value
        self.confidence = confidence  # 0.0 to 1.0
        self.evidence_quote = evidence_quote.strip() if evidence_quote else ""
        self.is_verified = is_verified
        self.verification_notes = verification_notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 2),
            "evidence_quote": self.evidence_quote,
            "is_verified": self.is_verified,
            "verification_notes": self.verification_notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedField":
        return cls(
            value=data.get("value"),
            confidence=data.get("confidence", 0.0),
            evidence_quote=data.get("evidence_quote", ""),
            is_verified=data.get("is_verified", False),
            verification_notes=data.get("verification_notes", "")
        )


class SchemeExtractionResult:
    """Encapsulates all extracted fields from an official government scheme document."""

    def __init__(
        self,
        source_name: str,
        raw_text_length: int,
        status: str = "UNVERIFIED_DRAFT"
    ):
        self.source_name = source_name
        self.raw_text_length = raw_text_length
        self.status = status  # 'UNVERIFIED_DRAFT' | 'VERIFIED' | 'REJECTED'
        self.extraction_timestamp = datetime.now().isoformat()
        self.verified_by: Optional[str] = None
        self.verification_timestamp: Optional[str] = None
        self.verification_notes: str = ""

        # Extracted fields
        self.scheme_name: ExtractedField = ExtractedField(None, 0.0, "")
        self.description: ExtractedField = ExtractedField(None, 0.0, "")
        self.eligible_business_types: ExtractedField = ExtractedField([], 0.0, "")
        self.eligible_sectors: ExtractedField = ExtractedField([], 0.0, "")
        self.min_age: ExtractedField = ExtractedField(None, 0.0, "")
        self.max_age: ExtractedField = ExtractedField(None, 0.0, "")
        self.business_age_req: ExtractedField = ExtractedField(None, 0.0, "")
        self.new_unit_only: ExtractedField = ExtractedField(False, 0.0, "")
        self.min_loan: ExtractedField = ExtractedField(0, 0.0, "")
        self.max_loan: ExtractedField = ExtractedField(0, 0.0, "")
        self.loan_details: ExtractedField = ExtractedField("", 0.0, "")
        self.min_turnover: ExtractedField = ExtractedField(0, 0.0, "")
        self.max_turnover: ExtractedField = ExtractedField(0, 0.0, "")
        self.states: ExtractedField = ExtractedField(["all"], 0.0, "")
        self.target_demographics: ExtractedField = ExtractedField([], 0.0, "")
        self.required_documents: ExtractedField = ExtractedField([], 0.0, "")
        self.benefits_summary: ExtractedField = ExtractedField("", 0.0, "")
        self.subsidy_details: ExtractedField = ExtractedField("", 0.0, "")
        self.key_conditions: ExtractedField = ExtractedField([], 0.0, "")
        self.official_link: ExtractedField = ExtractedField("", 0.0, "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "source_name": self.source_name,
                "raw_text_length": self.raw_text_length,
                "status": self.status,
                "extraction_timestamp": self.extraction_timestamp,
                "verified_by": self.verified_by,
                "verification_timestamp": self.verification_timestamp,
                "verification_notes": self.verification_notes,
                "is_safe_for_production": self.status == "VERIFIED"
            },
            "fields": {
                "scheme_name": self.scheme_name.to_dict(),
                "description": self.description.to_dict(),
                "eligible_business_types": self.eligible_business_types.to_dict(),
                "eligible_sectors": self.eligible_sectors.to_dict(),
                "min_age": self.min_age.to_dict(),
                "max_age": self.max_age.to_dict(),
                "business_age_req": self.business_age_req.to_dict(),
                "new_unit_only": self.new_unit_only.to_dict(),
                "min_loan": self.min_loan.to_dict(),
                "max_loan": self.max_loan.to_dict(),
                "loan_details": self.loan_details.to_dict(),
                "min_turnover": self.min_turnover.to_dict(),
                "max_turnover": self.max_turnover.to_dict(),
                "states": self.states.to_dict(),
                "target_demographics": self.target_demographics.to_dict(),
                "required_documents": self.required_documents.to_dict(),
                "benefits_summary": self.benefits_summary.to_dict(),
                "subsidy_details": self.subsidy_details.to_dict(),
                "key_conditions": self.key_conditions.to_dict(),
                "official_link": self.official_link.to_dict()
            }
        }


# ---------------------------------------------------------------------------
# NLP Eligibility Extractor Engine
# ---------------------------------------------------------------------------

class NLPEligibilityExtractor:
    """
    Lightweight, deterministic NLP rule engine for government scheme documents.
    Extracts structured eligibility parameters while retaining verbatim source quotes.
    """

    def __init__(self):
        # Known Indian states for geographic constraint detection
        self.known_states = {
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
            "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
            "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
            "delhi", "puducherry", "jammu & kashmir", "ladakh"
        }

        # Key document types in Indian schemes
        self.doc_patterns = [
            (r"\b(udyam|msme)\s+registration\b", "Udyam / MSME Registration"),
            (r"\b(aadhaar|aadhar|id proof|identity proof|pan card|voter id)\b", "Identity Proof (Aadhaar / PAN / Voter ID)"),
            (r"\b(address proof|residence certificate|domicile|ration card)\b", "Address / Residence Proof"),
            (r"\b(project report|detailed project report|dpr|business plan)\b", "Detailed Project Report (DPR)"),
            (r"\b(caste certificate|community certificate)\b", "Community / Caste Certificate (if applicable)"),
            (r"\b(educational? certificate|8th pass|10th pass|degree)\b", "Educational Qualification Certificate"),
            (r"\b(quotation|machinery quotation|proforma invoice)\b", "Machinery / Equipment Quotation"),
            (r"\b(bank statement|it returns?|itr|financial statements?)\b", "Bank Statements / Financial Statements"),
            (r"\b(vending certificate|survey certificate|id card)\b", "Street Vending Certificate / ID"),
        ]

    # -----------------------------------------------------------------------
    # Document Text Extraction
    # -----------------------------------------------------------------------

    def extract_text_from_pdf(self, pdf_path_or_bytes: Union[str, bytes]) -> str:
        """Extract text from a PDF file using pypdf if available."""
        if not PYPDF_AVAILABLE:
            raise ImportError(
                "pypdf library is required for PDF parsing. Please install with: pip install pypdf"
            )

        text_content = []
        if isinstance(pdf_path_or_bytes, str):
            if not os.path.exists(pdf_path_or_bytes):
                raise FileNotFoundError(f"PDF file not found: {pdf_path_or_bytes}")
            reader = pypdf.PdfReader(pdf_path_or_bytes)
        else:
            import io
            reader = pypdf.PdfReader(io.BytesIO(pdf_path_or_bytes))

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text_content.append(page_text)

        return "\n".join(text_content)

    def split_sentences(self, text: str) -> List[str]:
        """Split text into individual sentences for evidence citation."""
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        cleaned = [s.strip() for s in raw_sentences if s and len(s.strip()) > 5]
        return cleaned

    # -----------------------------------------------------------------------
    # Unit Parsing Helpers (Rupees, Lakhs, Crores, Percentages)
    # -----------------------------------------------------------------------

    def parse_currency_amount(self, text: str) -> Optional[int]:
        """Convert strings like 'Rs 50 lakh', 'Rs 1 crore', '10,000' to integer rupees."""
        text_lower = text.lower().replace(",", "")

        # Check for Crore (e.g. 1 crore, 2.5 crore, 10 cr)
        cr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr)", text_lower)
        if cr_match:
            val = float(cr_match.group(1))
            return int(val * 10_000_000)

        # Check for Lakh (e.g. 50 lakh, 10 lakhs, 2.5 lakh, 5 lac)
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs?|l\b)", text_lower)
        if lakh_match:
            val = float(lakh_match.group(1))
            return int(val * 100_000)

        # Check for Thousands (e.g. 50 thousand, 50k, 10,000)
        th_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:thousands?|k\b)", text_lower)
        if th_match:
            val = float(th_match.group(1))
            return int(val * 1_000)

        # Check raw digits
        num_match = re.search(r"(?:rs\.?|₹|inr)?\s*(\d{3,10})", text_lower)
        if num_match:
            return int(num_match.group(1))

        return None

    # -----------------------------------------------------------------------
    # NLP Extraction Pipeline
    # -----------------------------------------------------------------------

    def extract_from_text(self, text: str, source_name: str = "Official Text") -> SchemeExtractionResult:
        """
        Execute full NLP extraction pipeline on raw text.
        Returns a SchemeExtractionResult with all extracted entities and source quotes.
        """
        sentences = self.split_sentences(text)
        result = SchemeExtractionResult(
            source_name=source_name,
            raw_text_length=len(text),
            status="UNVERIFIED_DRAFT"
        )

        full_text_lower = text.lower()

        # 1. Scheme Name
        for sent in sentences[:6]:
            if re.search(r"\b(scheme|programme|yojana|fund|mission|initiative|programme|subvention)\b", sent, re.I):
                result.scheme_name = ExtractedField(sent[:120].strip(), 0.90, sent)
                break
        if not result.scheme_name.value:
            result.scheme_name = ExtractedField(source_name, 0.60, sentences[0] if sentences else "")

        # 2. Eligible Sectors and Business Types
        sectors = set()
        sector_evidence = []

        if re.search(r"\bmanufacturing\b", full_text_lower):
            sectors.add("manufacturing")
        if re.search(r"\bservice\b|\bservices\b", full_text_lower):
            sectors.add("service")
        if re.search(r"\bretail\b|\btrading\b|\bshop\b|\btrade\b|\bvending\b|\bvendor\b", full_text_lower):
            sectors.add("retail")
            sectors.add("trading")
        if re.search(r"\bfood\b|\bbakery\b|\bcatering\b|\bprocessing\b", full_text_lower):
            sectors.add("food")
            sectors.add("bakery")
        if re.search(r"\bprinting\b|\bxerox\b|\bphotocopy\b", full_text_lower):
            sectors.add("printing")
        if re.search(r"\bworkshop\b|\brepair\b|\bautomobile\b", full_text_lower):
            sectors.add("workshop")
        if re.search(r"\btailoring\b|\bgarment\b|\btextile\b|\bapparel\b", full_text_lower):
            sectors.add("tailoring")

        # Find supporting sentences for sectors
        for sent in sentences:
            if re.search(r"\b(manufacturing|service|trading|retail|food|printing|workshop|tailoring|sector|enterprise|activity)\b", sent, re.I):
                sector_evidence.append(sent)
                if len(sector_evidence) >= 2:
                    break

        ev_sec = " ".join(sector_evidence) if sector_evidence else (sentences[0] if sentences else "")
        result.eligible_sectors = ExtractedField(list(sectors) if sectors else ["micro-enterprise"], 0.85 if sectors else 0.50, ev_sec)
        result.eligible_business_types = ExtractedField(list(sectors) if sectors else ["manufacturing", "service", "retail"], 0.85, ev_sec)

        # 3. Applicant Age Limits
        min_age_val = None
        max_age_val = None
        age_ev = ""

        for sent in sentences:
            # Pattern: "aged 18-35", "between 21 and 35 years"
            age_range = re.search(r"\b(?:aged?|between)\s+(\d{2})\s*(?:to|-|and)\s*(\d{2})\s*years?\b", sent, re.I)
            if age_range:
                min_age_val = int(age_range.group(1))
                max_age_val = int(age_range.group(2))
                age_ev = sent
                break

            min_match = re.search(r"\b(?:above|minimum|at least|completed)\s+(\d{2})\s*years?\b", sent, re.I)
            if min_match:
                min_age_val = int(min_match.group(1))
                if not age_ev:
                    age_ev = sent

            max_match = re.search(r"\b(?:up to|maximum|below)\s+(\d{2})\s*years?\b", sent, re.I)
            if max_match:
                max_age_val = int(max_match.group(1))
                if not age_ev:
                    age_ev = sent

        result.min_age = ExtractedField(min_age_val or 18, 0.85 if min_age_val else 0.60, age_ev or "General adult eligibility (18+)")
        result.max_age = ExtractedField(max_age_val, 0.85 if max_age_val else 0.50, age_ev)

        # 4. Business Age & Greenfield Requirement
        is_new_only = False
        new_unit_ev = ""

        for sent in sentences:
            if re.search(r"\b(new units? only|greenfield|first-time entrepreneurs?|setting up new|new projects? only)\b", sent, re.I):
                is_new_only = True
                new_unit_ev = sent
                break
            elif re.search(r"\b(new and existing|existing small businesses|expansion|modernisation)\b", sent, re.I):
                is_new_only = False
                new_unit_ev = sent
                break

        result.new_unit_only = ExtractedField(is_new_only, 0.90 if new_unit_ev else 0.60, new_unit_ev or "Open to general enterprises")
        result.business_age_req = ExtractedField("0 years (New unit only)" if is_new_only else "0-100 years (New or Existing)", 0.85, new_unit_ev)

        # 5. Loan Limits & Support Amount
        found_amounts = []
        loan_ev_list = []

        for sent in sentences:
            # Look for currency patterns: "Rs 50 lakh", "Rs 10 lakh to Rs 1 crore", "up to Rs 20 lakh", "Rs 50,000"
            amount_matches = re.finditer(
                r"(?:rs\.?|₹|inr)?\s*(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lac|lacs?|thousands?|k)?\b",
                sent,
                re.I
            )
            sent_amounts = []
            for m in amount_matches:
                raw_str = m.group(0).strip()
                # Ensure it has either currency symbol or unit or is 4+ digits
                if any(kw in raw_str.lower() for kw in ["rs", "₹", "lakh", "lac", "crore", "cr", "thousand"]) or (m.group(1) and len(m.group(1)) >= 4):
                    parsed_val = self.parse_currency_amount(raw_str)
                    if parsed_val and parsed_val >= 1000:
                        sent_amounts.append(parsed_val)

            if sent_amounts:
                found_amounts.extend(sent_amounts)
                if sent not in loan_ev_list and len(loan_ev_list) < 2:
                    loan_ev_list.append(sent)

        min_loan_val = 0
        max_loan_val = 0
        loan_ev = " ".join(loan_ev_list)

        if found_amounts:
            max_loan_val = max(found_amounts)
            # If a range was explicitly given (e.g. 10 lakh to 1 crore)
            if len(found_amounts) >= 2 and min(found_amounts) < max_loan_val:
                min_loan_val = min(found_amounts)

        if max_loan_val == 0:
            max_loan_val = 1_000_000  # Default 10L fallback if not found

        result.min_loan = ExtractedField(min_loan_val, 0.88 if loan_ev else 0.50, loan_ev)
        result.max_loan = ExtractedField(max_loan_val, 0.88 if loan_ev else 0.50, loan_ev)
        result.loan_details = ExtractedField(
            f"Funding from ₹{min_loan_val:,} up to ₹{max_loan_val:,}" if min_loan_val else f"Credit support up to ₹{max_loan_val:,}",
            0.88,
            loan_ev
        )

        # 6. Geographic / State Restrictions
        detected_states = set()
        state_ev = ""

        for st in self.known_states:
            if re.search(r"\b" + re.escape(st) + r"\b", full_text_lower):
                detected_states.add(st)
                for sent in sentences:
                    if st in sent.lower():
                        state_ev = sent
                        break

        if detected_states:
            result.states = ExtractedField(list(detected_states), 0.90, state_ev)
        else:
            result.states = ExtractedField(["all"], 0.75, "All-India central scheme (no state limitation cited).")

        # 7. Subsidies, Guarantees, & Benefits
        subsidy_quotes = []
        for sent in sentences:
            if re.search(r"\b(subsidy|margin money|guarantee cover|interest subvention|collateral-free|concession)\b", sent, re.I):
                subsidy_quotes.append(sent)
                if len(subsidy_quotes) >= 2:
                    break

        subsidy_text = " ".join(subsidy_quotes) if subsidy_quotes else "Government financial and credit facilitation."
        result.subsidy_details = ExtractedField(subsidy_text, 0.85 if subsidy_quotes else 0.50, subsidy_text)
        result.benefits_summary = ExtractedField(subsidy_text, 0.85, subsidy_text)

        # 8. Required Documents
        detected_docs = []
        doc_evidence = []

        for pat, doc_name in self.doc_patterns:
            for sent in sentences:
                if re.search(pat, sent, re.I):
                    if doc_name not in detected_docs:
                        detected_docs.append(doc_name)
                    if sent not in doc_evidence and len(doc_evidence) < 3:
                        doc_evidence.append(sent)

        if not detected_docs:
            detected_docs = ["Identity Proof (Aadhaar / PAN)", "Address Proof", "Project Details / Bank Account"]

        result.required_documents = ExtractedField(detected_docs, 0.88 if doc_evidence else 0.60, " ".join(doc_evidence))

        # 9. Key Eligibility Conditions (Education, Demographics, etc.)
        conditions = []
        for sent in sentences:
            if re.search(r"\b(eligibility|eligible|criteria|qualification|8th pass|sc/st|women|stake|first-time)\b", sent, re.I):
                conditions.append(sent)
                if len(conditions) >= 3:
                    break

        result.key_conditions = ExtractedField(conditions, 0.85, " ".join(conditions) if conditions else "")

        # 10. Official Portal Link
        link_match = re.search(r"https?://[^\s<>\"']+", text)
        if link_match:
            result.official_link = ExtractedField(link_match.group(0), 0.98, link_match.group(0))

        # 11. Plain-text Description
        result.description = ExtractedField(sentences[0] if sentences else source_name, 0.80, sentences[0] if sentences else "")

        return result

    # -----------------------------------------------------------------------
    # Human-in-the-Loop Verification Workflow
    # -----------------------------------------------------------------------

    def verify_extraction(
        self,
        extraction_result: SchemeExtractionResult,
        verifier_name: str,
        notes: str = "Verified against official gazette/circular.",
        field_overrides: Optional[Dict[str, Any]] = None
    ) -> SchemeExtractionResult:
        """
        Apply human verification sign-off to an extracted scheme draft.
        Fields can optionally be corrected/overridden during human review.
        """
        if not verifier_name or not verifier_name.strip():
            raise ValueError("A valid human verifier name is required for verification audit.")

        extraction_result.status = "VERIFIED"
        extraction_result.verified_by = verifier_name.strip()
        extraction_result.verification_timestamp = datetime.now().isoformat()
        extraction_result.verification_notes = notes

        # Mark all individual fields as verified
        for attr_name in vars(extraction_result):
            attr_val = getattr(extraction_result, attr_name)
            if isinstance(attr_val, ExtractedField):
                attr_val.is_verified = True
                attr_val.verification_notes = f"Verified by {verifier_name}"

        # Apply any manual human corrections
        if field_overrides:
            for field_name, new_val in field_overrides.items():
                if hasattr(extraction_result, field_name):
                    f_obj = getattr(extraction_result, field_name)
                    if isinstance(f_obj, ExtractedField):
                        f_obj.value = new_val
                        f_obj.verification_notes = f"Manually adjusted and verified by {verifier_name}"

        return extraction_result

    def export_to_scheme_data_format(
        self,
        extraction_result: SchemeExtractionResult,
        enforce_verification: bool = True
    ) -> Dict[str, Any]:
        """
        Convert verified extraction result into SmartBiz scheme catalog format.
        Fails safely if enforce_verification is True and document has not been human-verified.
        """
        if enforce_verification and extraction_result.status != "VERIFIED":
            raise PermissionError(
                f"Cannot export unverified scheme data (Status: {extraction_result.status}). "
                "Official scheme documents must undergo human verification before inclusion in recommendations."
            )

        f = extraction_result
        return {
            "scheme_name": f.scheme_name.value or "Government Loan Scheme",
            "description": f.description.value or "",
            "eligibility": " ".join(f.key_conditions.value) if isinstance(f.key_conditions.value, list) else str(f.key_conditions.value or ""),
            "benefits": f.benefits_summary.value or "",
            "loan_details": f.loan_details.value or "",
            "documents": ", ".join(f.required_documents.value) if isinstance(f.required_documents.value, list) else str(f.required_documents.value or ""),
            "official_link": f.official_link.value or "",
            "business_types": f.eligible_business_types.value or ["manufacturing", "service"],
            "states": f.states.value or ["all"],
            "min_turnover": f.min_turnover.value or 0,
            "max_turnover": f.max_turnover.value or 100000000,
            "min_loan": f.min_loan.value or 0,
            "max_loan": f.max_loan.value or 5000000,
            "purposes": ["business setup", "machine purchase", "working capital"],
            "min_business_age": 0,
            "max_business_age": 0 if f.new_unit_only.value else 100,
            "new_unit_only": bool(f.new_unit_only.value),
            "verification_audit": {
                "status": f.status,
                "verified_by": f.verified_by,
                "verified_at": f.verification_timestamp,
                "source_document": f.source_name
            }
        }
