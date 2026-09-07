# SmartBiz scheme seed data
# Info summarized from public scheme literature (PMEGP, MUDRA, Stand-Up India, CGTMSE,
# TN government schemes) for demo/educational purposes. Always verify against the
# official source link before applying.

SCHEMES = [
    {
        "scheme_name": "PMEGP – Prime Minister's Employment Generation Programme",
        "description": (
            "A credit-linked subsidy scheme for setting up new micro-enterprises "
            "in the manufacturing or service sector. Aimed at first-time entrepreneurs, "
            "including new shop owners and small manufacturing units."
        ),
        "eligibility": (
            "Individuals above 18 years, new units only (not existing businesses), "
            "at least 8th pass for projects above Rs 10 lakh (manufacturing) or Rs 5 lakh (service)."
        ),
        "benefits": (
            "Government subsidy of 15%-35% of project cost depending on category and "
            "area (urban/rural); balance financed as a bank loan."
        ),
        "loan_details": "Manufacturing units up to Rs 50 lakh; service units up to Rs 20 lakh.",
        "documents": "ID proof, address proof, project report, caste certificate (if applicable), education certificate.",
        "official_link": "https://www.kviconline.gov.in/pmegpeportal/",
        "business_types": ["manufacturing", "service", "retail", "printing", "food", "bakery", "workshop"],
        "states": ["all"],
        "min_turnover": 0, "max_turnover": 10000000,
        "min_loan": 100000, "max_loan": 5000000,
        "purposes": ["machine purchase", "business setup", "new unit", "equipment"],
        "min_business_age": 0, "max_business_age": 0,  # 0 max means "new units only"
        "new_unit_only": True,
    },
    {
        "scheme_name": "PMMY – Pradhan Mantri MUDRA Yojana (Shishu/Kishor/Tarun)",
        "description": (
            "Collateral-free loans for non-farm micro and small enterprises, given in three "
            "stages based on the growth needs of the business: Shishu, Kishor and Tarun."
        ),
        "eligibility": (
            "Any Indian citizen with a business plan for a non-farm income generating activity "
            "in manufacturing, trading or services, including existing small businesses."
        ),
        "benefits": "No collateral required; competitive interest rates set by the lending bank.",
        "loan_details": "Shishu: up to Rs 50,000. Kishor: Rs 50,000-5 lakh. Tarun: Rs 5-10 lakh.",
        "documents": "ID proof, address proof, business proof, passport photo, quotation of machinery (if applicable).",
        "official_link": "https://www.mudra.org.in/",
        "business_types": ["retail", "manufacturing", "service", "printing", "food", "bakery", "workshop", "trading", "tailoring"],
        "states": ["all"],
        "min_turnover": 0, "max_turnover": 5000000,
        "min_loan": 0, "max_loan": 1000000,
        "purposes": ["working capital", "machine purchase", "business expansion", "business setup"],
        "min_business_age": 0, "max_business_age": 100,
        "new_unit_only": False,
    },
    {
        "scheme_name": "Stand-Up India Scheme",
        "description": (
            "Bank loans between Rs 10 lakh and Rs 1 crore for setting up a greenfield "
            "enterprise in manufacturing, services or trading, targeted at SC/ST and women entrepreneurs."
        ),
        "eligibility": (
            "SC/ST and/or women entrepreneurs above 18 years, for a greenfield (first-time) project; "
            "at least 51% shareholding/controlling stake must rest with the applicant."
        ),
        "benefits": "Composite loan covering both term loan and working capital; handholding support for the application.",
        "loan_details": "Rs 10 lakh to Rs 1 crore.",
        "documents": "ID and address proof, category certificate, project report, business registration documents.",
        "official_link": "https://www.standupmitra.in/",
        "business_types": ["manufacturing", "service", "retail", "trading"],
        "states": ["all"],
        "min_turnover": 0, "max_turnover": 20000000,
        "min_loan": 1000000, "max_loan": 10000000,
        "purposes": ["business setup", "new unit", "machine purchase"],
        "min_business_age": 0, "max_business_age": 0,
        "new_unit_only": True,
    },
    {
        "scheme_name": "CGTMSE – Credit Guarantee Fund Scheme for Micro and Small Enterprises",
        "description": (
            "A guarantee scheme that lets banks and NBFCs offer collateral-free loans to "
            "micro and small enterprises by covering the lender's risk instead."
        ),
        "eligibility": "New and existing micro and small enterprises in manufacturing or service activity.",
        "benefits": "No collateral or third-party guarantee needed for eligible loans; guarantee cover up to 85% in some categories.",
        "loan_details": "Collateral-free credit facility up to Rs 2 crore.",
        "documents": "Business registration proof, KYC documents, project/business details as required by the lending bank.",
        "official_link": "https://www.cgtmse.in/",
        "business_types": ["manufacturing", "service", "retail", "printing", "food", "bakery", "workshop"],
        "states": ["all"],
        "min_turnover": 0, "max_turnover": 15000000,
        "min_loan": 100000, "max_loan": 20000000,
        "purposes": ["machine purchase", "business expansion", "working capital", "business setup"],
        "min_business_age": 0, "max_business_age": 100,
        "new_unit_only": False,
    },
    {
        "scheme_name": "TN NEEDS – New Entrepreneur-cum-Enterprise Development Scheme (Tamil Nadu)",
        "description": (
            "A Tamil Nadu state scheme offering subsidized loans to educated youth in the state "
            "to set up new micro, small or medium enterprises."
        ),
        "eligibility": (
            "Tamil Nadu resident aged 21-35 (extended for some categories), minimum 8th standard pass, "
            "new project only."
        ),
        "benefits": "15% capital subsidy (up to a cap) and 3% annual interest subvention on the term loan.",
        "loan_details": "Project cost up to Rs 50 lakh for manufacturing, Rs 25 lakh for service enterprises.",
        "documents": "Tamil Nadu residence proof, educational certificate, project report, ID proof.",
        "official_link": "https://www.msmeonline.tn.gov.in/",
        "business_types": ["manufacturing", "service", "printing", "food", "bakery", "workshop"],
        "states": ["tamil nadu"],
        "min_turnover": 0, "max_turnover": 5000000,
        "min_loan": 100000, "max_loan": 5000000,
        "purposes": ["business setup", "new unit", "machine purchase"],
        "min_business_age": 0, "max_business_age": 0,
        "new_unit_only": True,
    },
    {
        "scheme_name": "TAHDCO Loan Scheme (Tamil Nadu)",
        "description": (
            "Loan and subsidy support from the Tamil Nadu Adi Dravidar Housing and Development "
            "Corporation for SC/ST entrepreneurs to start or expand small businesses."
        ),
        "eligibility": "SC/ST community members resident in Tamil Nadu, aged 18-55.",
        "benefits": "Subsidy component along with a bank-linked term loan; lower effective interest burden.",
        "loan_details": "Typically up to Rs 5 lakh depending on the specific sub-scheme.",
        "documents": "Community certificate, Tamil Nadu residence proof, ID proof, project details.",
        "official_link": "https://tahdco.com/",
        "business_types": ["retail", "service", "manufacturing", "printing", "food", "tailoring"],
        "states": ["tamil nadu"],
        "min_turnover": 0, "max_turnover": 2000000,
        "min_loan": 50000, "max_loan": 500000,
        "purposes": ["business setup", "business expansion", "machine purchase", "working capital"],
        "min_business_age": 0, "max_business_age": 100,
        "new_unit_only": False,
    },
    {
        "scheme_name": "PM SVANidhi – Street Vendor Loan Scheme",
        "description": (
            "Working-capital loans for urban street vendors and small stall owners to resume "
            "or grow their vending business, with repeat loans available on timely repayment."
        ),
        "eligibility": "Street vendors/hawkers operating in urban areas, with or without a vending certificate.",
        "benefits": "Interest subsidy on timely repayment; no collateral required.",
        "loan_details": "First loan up to Rs 10,000, second up to Rs 20,000, third up to Rs 50,000.",
        "documents": "Vending certificate/ID card (or survey certificate), ID proof.",
        "official_link": "https://pmsvanidhi.mohua.gov.in/",
        "business_types": ["retail", "food", "trading"],
        "states": ["all"],
        "min_turnover": 0, "max_turnover": 500000,
        "min_loan": 0, "max_loan": 50000,
        "purposes": ["working capital", "business expansion"],
        "min_business_age": 0, "max_business_age": 100,
        "new_unit_only": False,
    },
    {
        "scheme_name": "SIDBI Make in India Soft Loan Fund for MSMEs (SMILE)",
        "description": (
            "Soft loans with a longer repayment period, aimed at helping MSMEs meet the "
            "debt-equity ratio needed for expansion, modernisation or new-unit setup."
        ),
        "eligibility": "New and existing MSMEs registered under the MSME Development Act.",
        "benefits": "Longer repayment tenure and softer terms compared to a regular term loan.",
        "loan_details": "Loan amount generally starting from Rs 25 lakh and above.",
        "documents": "MSME/Udyam registration, financial statements, project report, KYC documents.",
        "official_link": "https://www.sidbi.in/",
        "business_types": ["manufacturing", "service"],
        "states": ["all"],
        "min_turnover": 500000, "max_turnover": 50000000,
        "min_loan": 2500000, "max_loan": 10000000,
        "purposes": ["business expansion", "machine purchase", "business setup"],
        "min_business_age": 0, "max_business_age": 100,
        "new_unit_only": False,
    },
]
