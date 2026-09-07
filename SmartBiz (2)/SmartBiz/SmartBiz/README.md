# SmartBiz

A discovery, comparison and information platform that helps small business
owners identify potentially relevant government financial schemes — it does
not provide loans itself.

## What's built (Phases 1–9 from the plan)

- Login / Register (Phase 1)
- Dashboard (Phase 2)
- Find Schemes form (Phase 3)
- Scheme database, seeded with 8 real-world Indian schemes: PMEGP, MUDRA,
  Stand-Up India, CGTMSE, TN-NEEDS, TAHDCO, PM SVANidhi, SIDBI SMILE (Phase 4)
- Results page with AI match scoring (Phase 5, Phase 9)
- Scheme details page with a plain-language explanation (Phase 6)
- Save + Search History (Phase 7)
- Compare up to 3 schemes side by side (Phase 8)

Phase 10 (testing with a real user) is up to you — the app is ready to try.

## How the "AI" matching works

`ai/scheme_matcher.py` is a transparent, rule-based scoring engine (not a
black-box model): it scores each scheme 0–100 against your business type,
location, loan amount, turnover, purpose, and business age, and explains
*why* each score was given. This is deliberately explainable — good for a
student project, and honest with the user about how the "match" was decided.
Swap in a real ML/LLM model later by replacing `match_schemes()` without
touching the rest of the app.

## Setup

```bash
cd SmartBiz
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install flask werkzeug
python3 app.py
```

Then open **http://localhost:5000** in your browser. The SQLite database
(`database.db`) is created and seeded with schemes automatically on first run.

## Project structure

```
SmartBiz/
├── app.py                 # Flask routes, auth, DB access
├── database.db             # created automatically on first run
├── ai/
│   ├── schemes_data.py     # seed data for 8 schemes
│   └── scheme_matcher.py   # matching / scoring logic
├── templates/               # Jinja2 HTML templates
└── static/
    ├── css/style.css
    └── js/script.js
```

## Notes for your project report

- Business details are **never** saved to the user's profile — only login
  info (name, email, mobile, password hash) is stored in `users`.
  Each search is logged in `search_history` instead.
- Every scheme page and the footer reminds the user to verify details
  against the official government link before applying — the match score
  is explicitly labelled as informational only.
- Passwords are hashed with Werkzeug's `generate_password_hash` /
  `check_password_hash` — never stored in plain text.
- To add more schemes, add entries to `ai/schemes_data.py` and delete
  `database.db` so it reseeds (or insert directly into the `schemes` table).
