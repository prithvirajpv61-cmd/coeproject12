# SmartBiz — Government Loan Schemes Discovery Platform

A lightweight, transparent web application that helps small business owners and entrepreneurs discover, evaluate, and compare Indian government loan schemes, subsidies, and credit guarantee programs.

---

## Overview

Navigating government schemes can be overwhelming for small business owners. **SmartBiz** simplifies this process with an explainable, rule-based matching engine. Users enter key business details (such as industry sector, location, turnover, loan requirement, and business age) to receive prioritized scheme recommendations with compatibility scores (0–100%) and clear eligibility explanations.

> **Disclaimer:** SmartBiz is an informational discovery and comparison platform, not a direct lender or financial institution. Scheme details should always be verified with official government portals before applying.

---

## Main Features

- **User Authentication & Profiles**: Secure user registration and login with password hashing (`Werkzeug`), session management, and self-service password reset.
- **Interactive Dashboard**: Overview of key statistics, profile completion progress, recent search history, bookmarked schemes, and quick links to official portals.
- **Smart Scheme Finder**: Dynamic search form collecting essential business criteria without storing sensitive business financials on the user's permanent profile.
- **Transparent AI Matching Engine**: Multi-factor rule-based algorithm that calculates 0–100% fit scores and provides plain-language explanations for each recommendation.
- **Scheme Details & Official Links**: Comprehensive breakdown of eligibility criteria, loan amounts, subsidy rates, required documents, and direct links to official portals.
- **Side-by-Side Comparison**: Compare up to 3 selected schemes simultaneously across eligibility, loan amounts, subsidies, and document requirements.
- **Bookmark & Search History**: Save preferred schemes across sessions and review past search parameters and results at any time.
- **Clean Responsive UI**: Modern design system built with semantic HTML, custom CSS, and vanilla JavaScript (no bulky third-party frontend frameworks required).

---

## Technologies Used

- **Backend**: Python 3, Flask
- **Security & Cryptography**: Werkzeug (`generate_password_hash`, `check_password_hash`), itsdangerous (`URLSafeTimedSerializer`)
- **Database**: SQLite3 (automatically initialized and seeded)
- **Frontend / Templating**: Jinja2 HTML Templates, Vanilla CSS, Vanilla JavaScript

---

## Project Structure

```text
project/
│
├── static/
│   ├── script.js               # Interactive UI logic, AJAX save/unsave, compare bar
│   └── style.css               # Design system, variables, and responsive layout
│
├── templates/
│   ├── base.html               # Base layout, navigation header, and footer
│   ├── compare.html            # Side-by-side scheme comparison table
│   ├── dashboard.html          # Main user dashboard with stats & quick actions
│   ├── find-schemes.html       # Business requirements input form
│   ├── forgot-password.html    # Password reset request page
│   ├── history.html            # Past search history log
│   ├── login.html              # User login page
│   ├── profile.html            # User account settings & password management
│   ├── register.html           # Account creation page
│   ├── reset-password.html     # Password update page
│   ├── results.html            # Ranked scheme results with match scores
│   ├── saved-schemes.html      # User's bookmarked schemes
│   └── scheme-details.html     # Detailed scheme view with plain explanation
│
├── .gitignore                  # Git ignore rules for Python, SQLite, & cache
├── app.py                      # Core Flask application, routes, and DB setup
├── README.md                   # Project documentation
├── requirements.txt            # Python package dependencies
├── scheme_matcher.py           # Rule-based scheme matching & scoring engine
└── schemes_data.py             # Seed dataset of government schemes
```

---

## Installation & Setup

### Prerequisites

- Python 3.8 or higher installed on your system.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd project
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Database Configuration

- The application uses a local **SQLite** database (`database.db`).
- **Auto-Initialization**: You do not need to manually create or seed the database. When the application starts, it automatically creates the required tables (`users`, `schemes`, `saved_schemes`, `search_history`) and seeds the database with verified government schemes (PMEGP, MUDRA, Stand-Up India, CGTMSE, TN NEEDS, TAHDCO, PM SVANidhi, SIDBI SMILE).
- `database.db` is ignored by `.gitignore` so local user accounts and runtime test data are not committed to GitHub.

---

## Government Schemes Included

1. **PMEGP** (Prime Minister's Employment Generation Programme) — Credit-linked subsidy for new micro-enterprises.
2. **PMMY / MUDRA** (Pradhan Mantri MUDRA Yojana) — Collateral-free loans up to ₹10 Lakhs (Shishu, Kishor, Tarun).
3. **Stand-Up India Scheme** — Greenfield enterprise loans (₹10 Lakhs to ₹1 Crore) for SC/ST and Women entrepreneurs.
4. **CGTMSE** (Credit Guarantee Fund Trust for Micro and Small Enterprises) — Collateral-free credit facility up to ₹2 Crores.
5. **TN NEEDS** — Subsidized loans for educated youth in Tamil Nadu.
6. **TAHDCO Scheme** — Economic development subsidies for SC/ST entrepreneurs in Tamil Nadu.
7. **PM SVANidhi** — Micro-credit working capital loans for urban street vendors.
8. **SIDBI SMILE** — Soft loans and term loans for MSMEs to meet required debt-equity ratios.

---

## License & Academic Note

Developed as an academic demonstration project for small business government scheme discovery and assistance.
