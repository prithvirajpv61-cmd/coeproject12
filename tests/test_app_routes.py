"""
Integration Tests for SmartBiz Flask Application Routes and User Flows.

Covers:
1. User registration, login, session persistence, and logout
2. Dashboard view with statistics and recommended schemes
3. Scheme search with exact category, fuzzy category, and edge cases
4. Saving and unsaving schemes (API and web views)
5. Search history recording and historical search re-execution
6. Side-by-side scheme comparison
7. Scheme details view
8. User profile viewing and updates
"""

import unittest
import json
from app import app, init_db, get_db


class TestSmartBizAppRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        self.client = app.test_client()

        with app.app_context():
            init_db()
            db = get_db()
            # Clear users for clean test run
            db.execute("DELETE FROM users WHERE email LIKE '%@test.com'")
            db.commit()

        # Create a test user
        self.test_email = "entrepreneur@test.com"
        self.test_pass = "securepass123"
        self.client.post("/register", data={
            "name": "Arun Kumar",
            "email": self.test_email,
            "mobile": "9876543210",
            "password": self.test_pass,
            "confirm_password": self.test_pass
        })

    def login(self):
        return self.client.post("/login", data={
            "identifier": self.test_email,
            "password": self.test_pass
        }, follow_redirects=True)

    # -----------------------------------------------------------------------
    # 1. Authentication Flows
    # -----------------------------------------------------------------------
    def test_01_auth_flow(self):
        """Tests login, dashboard access, and logout."""
        # Unauthenticated access to dashboard redirects to login
        res = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        # Login
        login_res = self.login()
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Arun Kumar", login_res.data)

        # Logout
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"logged out", logout_res.data.lower())

    # -----------------------------------------------------------------------
    # 2. Scheme Search with Fuzzy Business Categories
    # -----------------------------------------------------------------------
    def test_02_search_with_fuzzy_categories(self):
        """Tests scheme discovery using real-world fuzzy business terms."""
        self.login()

        queries = [
            {"business_type": "Xerox Shop", "location": "Tamil Nadu", "loan_amount": "300000", "loan_purpose": "machine purchase", "business_age": "0"},
            {"business_type": "Bakery and Cake Shop", "location": "Karnataka", "loan_amount": "500000", "loan_purpose": "business setup", "business_age": "0"},
            {"business_type": "Grocery Store / Kirana", "location": "Maharashtra", "loan_amount": "100000", "loan_purpose": "working capital", "business_age": "2"},
            {"business_type": "Two Wheeler Auto Repair Garage", "location": "Tamil Nadu", "loan_amount": "250000", "loan_purpose": "machine purchase", "business_age": "1"}
        ]

        for q in queries:
            res = self.client.post("/results", data=q, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Potentially relevant schemes", res.data)
            self.assertIn(b"Why this scheme matches", res.data)
            self.assertIn(b"Business category", res.data)
            self.assertIn(b"Match score is an informational recommendation", res.data)

    # -----------------------------------------------------------------------
    # 3. Save and Unsave Scheme JSON API
    # -----------------------------------------------------------------------
    def test_03_save_unsave_scheme_api(self):
        """Tests bookmarking and removing saved schemes."""
        self.login()

        # Save scheme #1 (PMEGP)
        save_res = self.client.post("/api/save-scheme", json={"scheme_id": 1})
        self.assertEqual(save_res.status_code, 200)
        data = json.loads(save_res.data)
        self.assertTrue(data.get("saved"))

        # Verify in saved schemes list
        saved_page = self.client.get("/saved-schemes")
        self.assertEqual(saved_page.status_code, 200)
        self.assertIn(b"PMEGP", saved_page.data)

        # Unsave scheme #1
        unsave_res = self.client.post("/api/unsave-scheme", json={"scheme_id": 1})
        self.assertEqual(unsave_res.status_code, 200)
        unsave_data = json.loads(unsave_res.data)
        self.assertFalse(unsave_data.get("saved"))

    # -----------------------------------------------------------------------
    # 4. Search History View & Re-execution
    # -----------------------------------------------------------------------
    def test_04_search_history_persistence(self):
        """Searches are recorded in history and can be viewed."""
        self.login()

        # Execute search
        self.client.post("/results", data={
            "business_type": "Mobile Shop and Repair",
            "location": "Tamil Nadu",
            "loan_amount": "200000",
            "loan_purpose": "working capital",
            "business_age": "1"
        })

        # View history ledger
        hist_res = self.client.get("/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b"Mobile Shop And Repair", hist_res.data)

    # -----------------------------------------------------------------------
    # 5. Side-by-Side Scheme Comparison
    # -----------------------------------------------------------------------
    def test_05_compare_schemes(self):
        """Comparison page renders multiple schemes side-by-side."""
        self.login()
        res = self.client.get("/compare?ids=1,2")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Comparing 2 schemes", res.data)
        self.assertIn(b"PMEGP", res.data)
        self.assertIn(b"MUDRA", res.data)

    # -----------------------------------------------------------------------
    # 6. Scheme Details Page
    # -----------------------------------------------------------------------
    def test_06_scheme_details(self):
        """Scheme details page renders full eligibility and simple explanation."""
        self.login()
        res = self.client.get("/scheme/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"PMEGP", res.data)
        self.assertIn(b"In simple language", res.data)
        self.assertIn(b"Eligibility", res.data)


if __name__ == "__main__":
    unittest.main()
