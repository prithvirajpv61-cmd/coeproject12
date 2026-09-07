import os
import sqlite3
import json
import re
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

from ai.schemes_data import SCHEMES
from ai.scheme_matcher import match_schemes, explain_simple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartbiz-dev-secret-change-in-production")
RESET_TOKEN_SALT = "smartbiz-password-reset-salt"
RESET_TOKEN_MAX_AGE = 900  # 15 minutes


# ---------------------------------------------------------------------------
# Validation and Token helpers
# ---------------------------------------------------------------------------

def is_valid_email(val: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val.strip()))


def is_valid_mobile(val: str) -> bool:
    digits = re.sub(r"[^\d]", "", val.strip())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return len(digits) == 10


def get_reset_serializer():
    return URLSafeTimedSerializer(app.secret_key)


def generate_reset_token(user_id: int) -> str:
    serializer = get_reset_serializer()
    return serializer.dumps({"user_id": user_id}, salt=RESET_TOKEN_SALT)


def verify_reset_token(token: str, max_age: int = RESET_TOKEN_MAX_AGE):
    serializer = get_reset_serializer()
    try:
        data = serializer.loads(token, salt=RESET_TOKEN_SALT, max_age=max_age)
        return data.get("user_id")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    fresh = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS schemes (
            scheme_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_name TEXT NOT NULL,
            description TEXT,
            eligibility TEXT,
            benefits TEXT,
            loan_details TEXT,
            documents TEXT,
            official_link TEXT,
            raw_json TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS saved_schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            scheme_id INTEGER NOT NULL,
            saved_date TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE,
            UNIQUE(user_id, scheme_id)
        );

        CREATE TABLE IF NOT EXISTS search_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_type TEXT,
            location TEXT,
            turnover INTEGER,
            loan_amount INTEGER,
            loan_purpose TEXT,
            business_age INTEGER,
            search_date TEXT DEFAULT (datetime('now')),
            search_results TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """
    )
    db.commit()

    # Seed schemes only once
    count = db.execute("SELECT COUNT(*) FROM schemes").fetchone()[0]
    if count == 0:
        for s in SCHEMES:
            db.execute(
                """INSERT INTO schemes
                   (scheme_name, description, eligibility, benefits, loan_details,
                    documents, official_link, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s["scheme_name"], s["description"], s["eligibility"], s["benefits"],
                    s["loan_details"], s["documents"], s["official_link"], json.dumps(s),
                ),
            )
        db.commit()
    db.close()
    return fresh


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "Authentication required", "login_url": url_for("login")}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"current_user_name": session.get("user_name")}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        db = get_db()
        existing = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email already exists. Please log in.", "error")
            return render_template("register.html")

        db.execute(
            "INSERT INTO users (name, email, mobile, password) VALUES (?, ?, ?, ?)",
            (name, email, mobile, generate_password_hash(password)),
        )
        db.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    identifier = ""
    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("email") or "").strip()
        password = request.form.get("password", "")

        if not identifier:
            flash("Please enter your email/mobile number.", "error")
            return render_template("login.html", identifier=identifier)

        if not password:
            flash("Please enter your password.", "error")
            return render_template("login.html", identifier=identifier)

        if not (is_valid_email(identifier) or is_valid_mobile(identifier)):
            flash("Please enter a valid email address or 10-digit mobile number.", "error")
            return render_template("login.html", identifier=identifier)

        db = get_db()
        email_norm = identifier.lower()
        digits = re.sub(r"[^\d]", "", identifier)
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? OR mobile = ? OR mobile = ?",
            (email_norm, identifier, digits),
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email/mobile number or password.", "error")
        return render_template("login.html", identifier=identifier)

    return render_template("login.html", identifier=identifier)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    identifier = ""
    reset_url = None
    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("email") or "").strip()

        if not identifier:
            flash("Please enter your email/mobile number.", "error")
            return render_template("forgot-password.html", identifier=identifier)

        if not (is_valid_email(identifier) or is_valid_mobile(identifier)):
            flash("Please enter a valid email address or 10-digit mobile number.", "error")
            return render_template("forgot-password.html", identifier=identifier)

        db = get_db()
        email_norm = identifier.lower()
        digits = re.sub(r"[^\d]", "", identifier)
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? OR mobile = ? OR mobile = ?",
            (email_norm, identifier, digits),
        ).fetchone()

        if not user:
            flash("No account found with that email address or mobile number.", "error")
            return render_template("forgot-password.html", identifier=identifier)

        token = generate_reset_token(user["user_id"])
        reset_url = url_for("reset_password", token=token)

        # Integration note: In production, trigger send_password_reset_email/sms(user, reset_url)
        flash("Password reset link ready. Click 'Continue to Reset Password' below to proceed.", "success")
        return render_template("forgot-password.html", identifier=identifier, reset_url=reset_url)

    return render_template("forgot-password.html", identifier=identifier)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    token = request.args.get("token") or request.form.get("token") or ""
    if not token:
        flash("Password reset token is missing. Please request a new link.", "error")
        return redirect(url_for("forgot_password"))

    user_id = verify_reset_token(token)
    if not user_id:
        flash("Password reset link is invalid or has expired. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        flash("User account not found.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or not confirm_password:
            flash("Please enter and confirm your new password.", "error")
            return render_template("reset-password.html", token=token)

        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
            return render_template("reset-password.html", token=token)

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("reset-password.html", token=token)

        hashed = generate_password_hash(new_password)
        db.execute("UPDATE users SET password = ? WHERE user_id = ?", (hashed, user_id))
        db.commit()

        flash("Your password has been reset successfully. Please log in with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("reset-password.html", token=token)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Core app routes
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (session["user_id"],)).fetchone()

    saved_count = db.execute(
        "SELECT COUNT(*) FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
    ).fetchone()[0]

    history_count = db.execute(
        "SELECT COUNT(*) FROM search_history WHERE user_id = ?", (session["user_id"],)
    ).fetchone()[0]

    total_schemes_count = db.execute("SELECT COUNT(*) FROM schemes").fetchone()[0]

    has_mobile = bool(user and user["mobile"] and user["mobile"].strip())
    has_activity = history_count > 0 or saved_count > 0
    profile_completion = 50 + (25 if has_mobile else 0) + (25 if has_activity else 0)

    recent_searches = db.execute(
        "SELECT * FROM search_history WHERE user_id = ? ORDER BY history_id DESC LIMIT 3",
        (session["user_id"],),
    ).fetchall()

    recent_saved = db.execute(
        """SELECT s.scheme_id, s.scheme_name, s.description, s.loan_details, ss.saved_date, s.raw_json
           FROM saved_schemes ss
           JOIN schemes s ON ss.scheme_id = s.scheme_id
           WHERE ss.user_id = ?
           ORDER BY ss.id DESC LIMIT 3""",
        (session["user_id"],),
    ).fetchall()

    featured_rows = db.execute("SELECT * FROM schemes ORDER BY scheme_id ASC LIMIT 3").fetchall()
    featured_schemes = [dict(row_to_scheme(r)) for r in featured_rows]

    saved_ids = set(
        r[0] for r in db.execute(
            "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
        ).fetchall()
    )

    hour = datetime.now().hour
    if hour < 12:
        greeting_time = "Good morning"
    elif hour < 17:
        greeting_time = "Good afternoon"
    else:
        greeting_time = "Good evening"

    return render_template(
        "dashboard.html",
        user=user,
        saved_count=saved_count,
        history_count=history_count,
        total_schemes_count=total_schemes_count,
        profile_completion=profile_completion,
        recent_searches=recent_searches,
        recent_saved=recent_saved,
        featured_schemes=featured_schemes,
        saved_ids=saved_ids,
        greeting_time=greeting_time,
    )


@app.route("/find-schemes")
@login_required
def find_schemes():
    return render_template("find-schemes.html")


def _clean_int(val, default=0):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    cleaned = re.sub(r"[^\d]", "", str(val).strip())
    return int(cleaned) if cleaned else default


def _run_match(form):
    user_input = {
        "business_type": str(form.get("business_type") or "").strip(),
        "location": str(form.get("location") or "").strip(),
        "annual_turnover": _clean_int(form.get("annual_turnover")),
        "loan_amount": _clean_int(form.get("loan_amount")),
        "loan_purpose": str(form.get("loan_purpose") or "").strip(),
        "business_age": _clean_int(form.get("business_age")),
        "registration_status": str(form.get("registration_status") or "").strip(),
        "previous_loan": str(form.get("previous_loan") or "").strip(),
    }
    all_schemes = [dict(row_to_scheme(r)) for r in get_db().execute("SELECT * FROM schemes")]
    ranked = match_schemes(all_schemes, user_input)
    return user_input, ranked


def row_to_scheme(row):
    data = json.loads(row["raw_json"])
    data["scheme_id"] = row["scheme_id"]
    return data


@app.route("/results", methods=["GET", "POST"])
@login_required
def results():
    db = get_db()
    if request.method == "POST":
        user_input, ranked = _run_match(request.form)
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO search_history
               (user_id, business_type, location, turnover, loan_amount, loan_purpose,
                business_age, search_results)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session["user_id"], user_input["business_type"], user_input["location"],
                user_input["annual_turnover"], user_input["loan_amount"], user_input["loan_purpose"],
                user_input["business_age"], json.dumps([r["scheme_id"] for r in ranked[:10]]),
            ),
        )
        db.commit()
        session["latest_history_id"] = cursor.lastrowid
        session["latest_user_input"] = user_input

        saved_ids = {
            r["scheme_id"] for r in db.execute(
                "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
            )
        }
        return render_template(
            "results.html", user_input=user_input, schemes=ranked[:10], saved_ids=saved_ids
        )
    else:
        # GET request handling for /results (e.g. following browser refresh or redirect)
        latest_id = session.get("latest_history_id")
        if latest_id:
            row = db.execute(
                "SELECT * FROM search_history WHERE history_id = ? AND user_id = ?",
                (latest_id, session["user_id"]),
            ).fetchone()
            if row:
                user_input = {
                    "business_type": row["business_type"], "location": row["location"],
                    "annual_turnover": row["turnover"], "loan_amount": row["loan_amount"],
                    "loan_purpose": row["loan_purpose"], "business_age": row["business_age"],
                    "registration_status": "udyam", "previous_loan": "none"
                }
                _, ranked = _run_match(user_input)
                saved_ids = {
                    r["scheme_id"] for r in db.execute(
                        "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
                    )
                }
                return render_template(
                    "results.html", user_input=user_input, schemes=ranked[:10], saved_ids=saved_ids, from_history=True
                )
        return redirect(url_for("find_schemes"))


@app.route("/scheme/<int:scheme_id>")
@login_required
def scheme_details(scheme_id):
    db = get_db()
    row = db.execute("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id,)).fetchone()
    if not row:
        flash("Scheme not found.", "error")
        return redirect(url_for("find_schemes"))
    scheme = row_to_scheme(row)
    is_saved = db.execute(
        "SELECT 1 FROM saved_schemes WHERE user_id = ? AND scheme_id = ?",
        (session["user_id"], scheme_id),
    ).fetchone() is not None
    simple_explanation = explain_simple(scheme)
    return render_template("scheme-details.html", scheme=scheme, is_saved=is_saved,
                            simple_explanation=simple_explanation)


@app.route("/compare")
@login_required
def compare():
    ids = request.args.get("ids", "")
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()][:3]
    db = get_db()
    schemes = []
    for sid in id_list:
        row = db.execute("SELECT * FROM schemes WHERE scheme_id = ?", (sid,)).fetchone()
        if row:
            schemes.append(row_to_scheme(row))
    return render_template("compare.html", schemes=schemes)


# ---------------------------------------------------------------------------
# Save / Unsave Endpoints (JSON API + Form POST Support)
# ---------------------------------------------------------------------------

@app.route("/api/save-scheme", methods=["POST"])
@app.route("/save/<int:scheme_id>", methods=["POST"])
@login_required
def save_scheme(scheme_id=None):
    if scheme_id is None:
        if request.is_json:
            scheme_id = request.json.get("scheme_id")
        else:
            scheme_id = request.form.get("scheme_id")

    if not scheme_id:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Missing scheme_id"}), 400
        flash("Invalid scheme.", "error")
        return redirect(request.referrer or url_for("dashboard"))

    scheme_id = int(scheme_id)
    db = get_db()

    # Verify scheme exists
    scheme = db.execute("SELECT scheme_name FROM schemes WHERE scheme_id = ?", (scheme_id,)).fetchone()
    if not scheme:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Scheme not found"}), 404
        flash("Scheme not found.", "error")
        return redirect(request.referrer or url_for("dashboard"))

    try:
        db.execute(
            "INSERT INTO saved_schemes (user_id, scheme_id) VALUES (?, ?)",
            (session["user_id"], scheme_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # Already saved, keep existing record
        pass

    if request.is_json or request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "saved": True,
            "scheme_id": scheme_id,
            "scheme_name": scheme["scheme_name"],
            "message": "Scheme saved successfully."
        })

    flash("Scheme saved.", "success")
    return redirect(request.referrer or url_for("saved_schemes"))


@app.route("/api/unsave-scheme", methods=["POST", "DELETE"])
@app.route("/unsave/<int:scheme_id>", methods=["POST", "DELETE"])
@login_required
def unsave_scheme(scheme_id=None):
    if scheme_id is None:
        if request.is_json:
            scheme_id = request.json.get("scheme_id")
        else:
            scheme_id = request.form.get("scheme_id")

    if not scheme_id:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Missing scheme_id"}), 400
        flash("Invalid scheme.", "error")
        return redirect(request.referrer or url_for("saved_schemes"))

    scheme_id = int(scheme_id)
    db = get_db()

    db.execute(
        "DELETE FROM saved_schemes WHERE user_id = ? AND scheme_id = ?",
        (session["user_id"], scheme_id),
    )
    db.commit()

    if request.is_json or request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "saved": False,
            "scheme_id": scheme_id,
            "message": "Scheme removed from saved."
        })

    flash("Removed from saved schemes.", "success")
    return redirect(request.referrer or url_for("saved_schemes"))


@app.route("/api/saved-schemes", methods=["GET"])
@login_required
def api_saved_schemes():
    db = get_db()
    rows = db.execute(
        "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
    ).fetchall()
    saved_ids = [r["scheme_id"] for r in rows]
    return jsonify({"success": True, "saved_ids": saved_ids, "count": len(saved_ids)})


@app.route("/saved-schemes")
@login_required
def saved_schemes():
    db = get_db()
    rows = db.execute(
        """SELECT s.* FROM schemes s
           JOIN saved_schemes ss ON ss.scheme_id = s.scheme_id
           WHERE ss.user_id = ? ORDER BY ss.saved_date DESC""",
        (session["user_id"],),
    ).fetchall()
    schemes = [row_to_scheme(r) for r in rows]
    return render_template("saved-schemes.html", schemes=schemes)


@app.route("/history")
@login_required
def history():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM search_history WHERE user_id = ? ORDER BY search_date DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("history.html", history=rows)


@app.route("/history/<int:history_id>")
@login_required
def history_view(history_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM search_history WHERE history_id = ? AND user_id = ?",
        (history_id, session["user_id"]),
    ).fetchone()
    if not row:
        flash("Search not found.", "error")
        return redirect(url_for("history"))

    user_input = {
        "business_type": row["business_type"], "location": row["location"],
        "annual_turnover": row["turnover"], "loan_amount": row["loan_amount"],
        "loan_purpose": row["loan_purpose"], "business_age": row["business_age"],
        "registration_status": "udyam", "previous_loan": "none"
    }
    _, ranked = _run_match(user_input)
    saved_ids = {
        r["scheme_id"] for r in db.execute(
            "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (session["user_id"],)
        )
    }
    return render_template("results.html", user_input=user_input, schemes=ranked[:10],
                            saved_ids=saved_ids, from_history=True)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_info":
            name = request.form.get("name", "").strip()
            mobile = request.form.get("mobile", "").strip()
            db.execute(
                "UPDATE users SET name = ?, mobile = ? WHERE user_id = ?",
                (name, mobile, session["user_id"]),
            )
            db.commit()
            session["user_name"] = name
            flash("Profile updated.", "success")
        elif action == "change_password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            user = db.execute(
                "SELECT * FROM users WHERE user_id = ?", (session["user_id"],)
            ).fetchone()
            if not check_password_hash(user["password"], current):
                flash("Current password is incorrect.", "error")
            elif len(new) < 6:
                flash("New password must be at least 6 characters.", "error")
            else:
                db.execute(
                    "UPDATE users SET password = ? WHERE user_id = ?",
                    (generate_password_hash(new), session["user_id"]),
                )
                db.commit()
                flash("Password changed.", "success")
        return redirect(url_for("profile"))

    user = db.execute("SELECT * FROM users WHERE user_id = ?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
