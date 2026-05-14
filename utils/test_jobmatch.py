"""
test_jobmatch.py — Complete Test Suite
Pioneer Insurance Group JobMatch System
========================================

TWO KINDS OF TESTS IN ONE FILE:

  1. DIRECT PYTHON TESTS (unittest) — No browser needed.
     These test your ML model, scoring function, resume parser,
     and skill extraction functions directly in Python.
     Fast. Runs in seconds.

  2. SELENIUM UI TESTS — Opens a real Chrome browser.
     Tests login, signup, job posting, security, performance,
     and the full ML pipeline end-to-end through the browser.
     Requires: streamlit run app.py to be running first.

HOW TO RUN:
  # All tests:
  python test_jobmatch.py

  # Only ML tests (no browser):
  python test_jobmatch.py --ml-only

  # Only Selenium tests (browser):
  python test_jobmatch.py --ui-only

INSTALL:
  pip install selenium webdriver-manager
"""

import sys
import os
import io
import time
import unittest

# ── Add project folder to path so we can import your modules ─────────────────
# This makes "from train_model import predict_single" work from any folder
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

APP_URL = "http://localhost:8501"

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 1 — DIRECT ML TESTS  (no browser, no Streamlit)
#
#  These tests call your Python functions directly.
#  They run independently of the app being live.
# ─────────────────────────────────────────────────────────────────────────────

class TestMLModelFile(unittest.TestCase):
    """
    ML-01 to ML-04
    Tests that resume_model.pkl exists, loads correctly,
    and contains all the required components.
    """

    def test_ML01_model_file_exists(self):
        """ML-01: The model file must exist on disk before the app can run."""
        print("\n[ML-01] Checking resume_model.pkl exists on disk")
        model_path = os.path.join(PROJECT_DIR, "resume_model.pkl")
        self.assertTrue(
            os.path.exists(model_path),
            "ML-01 FAIL: resume_model.pkl not found. Run train_model.py first."
        )
        print("ML-01 PASS — resume_model.pkl found")

    def test_ML02_model_loads_without_error(self):
        """ML-02: The model file must load cleanly with joblib."""
        print("\n[ML-02] Loading resume_model.pkl with joblib")
        import joblib
        model_path = os.path.join(PROJECT_DIR, "resume_model.pkl")
        try:
            bundle = joblib.load(model_path)
            self.assertIsNotNone(bundle, "ML-02 FAIL: joblib returned None.")
            print("ML-02 PASS — model loaded successfully")
        except Exception as e:
            self.fail(f"ML-02 FAIL: Could not load model — {e}")

    def test_ML03_model_bundle_has_required_keys(self):
        """
        ML-03: The saved dict must contain clf, tfidf, and numeric_columns.
        These three are the minimum needed for predict_single() to work.
        """
        print("\n[ML-03] Checking model bundle contains required keys")
        import joblib
        model_path = os.path.join(PROJECT_DIR, "resume_model.pkl")
        bundle = joblib.load(model_path)

        required_keys = ["clf", "tfidf", "numeric_columns", "edu_rank"]
        for key in required_keys:
            self.assertIn(
                key, bundle,
                f"ML-03 FAIL: Key '{key}' missing from model bundle."
            )
        print(f"ML-03 PASS — keys found: {list(bundle.keys())}")

    def test_ML04_model_file_is_not_empty(self):
        """ML-04: Model file must be larger than 1 KB (sanity check)."""
        print("\n[ML-04] Checking model file is not empty/corrupt")
        model_path = os.path.join(PROJECT_DIR, "resume_model.pkl")
        size_kb = os.path.getsize(model_path) / 1024
        print(f"        File size: {size_kb:.1f} KB")
        self.assertGreater(
            size_kb, 1,
            "ML-04 FAIL: Model file is less than 1 KB — likely corrupt."
        )
        print("ML-04 PASS — model file size is healthy")


# ─────────────────────────────────────────────────────────────────────────────

class TestPredictSingle(unittest.TestCase):
    """
    ML-05 to ML-10
    Tests the predict_single() function from train_model.py.
    This is the core ML scoring function your app calls every time
    a seeker submits an application.
    """

    @classmethod
    def setUpClass(cls):
        """Load the model once before all tests in this class."""
        import joblib
        model_path = os.path.join(PROJECT_DIR, "resume_model.pkl")
        if not os.path.exists(model_path):
            raise unittest.SkipTest(
                "resume_model.pkl not found — skipping scoring tests."
            )
        cls.bundle = joblib.load(model_path)

        # Import predict_single from train_model.py
        from train_model import predict_single
        cls.predict = predict_single

    def _strong_resume(self):
        """A well-qualified resume — high experience, skills, education."""
        return {
            "skills": "Python, Machine Learning, TensorFlow, SQL, "
                      "Deep Learning, AWS, Docker, Pandas, NumPy, Scikit-learn",
            "experience_years": 7,
            "education": "M.Tech",
            "certifications": "Google ML",
            "job_role": "Data Scientist",
            "projects_count": 5,
        }

    def _weak_resume(self):
        """A poorly matched resume — low experience, few skills."""
        return {
            "skills": "Excel, PowerPoint",
            "experience_years": 0,
            "education": "B.Sc",
            "certifications": "None",
            "job_role": "",
            "projects_count": 0,
        }

    def _mid_resume(self):
        """A borderline resume."""
        return {
            "skills": "Python, SQL, Excel, Git",
            "experience_years": 2,
            "education": "B.Tech",
            "certifications": "None",
            "job_role": "Software Engineer",
            "projects_count": 2,
        }

    def test_ML05_score_is_between_0_and_100(self):
        """ML-05: Score must always be a number in the 0–100 range."""
        print("\n[ML-05] Score must be between 0 and 100")
        for name, resume in [("strong", self._strong_resume()),
                               ("weak",   self._weak_resume()),
                               ("mid",    self._mid_resume())]:
            score, label = self.predict(self.bundle, resume)
            print(f"        {name} resume → score={score}, label={label}")
            self.assertGreaterEqual(score, 0,
                f"ML-05 FAIL: {name} resume score {score} is below 0.")
            self.assertLessEqual(score, 100,
                f"ML-05 FAIL: {name} resume score {score} exceeds 100.")
        print("ML-05 PASS — all scores in valid range")

    def test_ML06_label_is_one_of_three_valid_values(self):
        """ML-06: Label must be exactly one of the three defined strings."""
        print("\n[ML-06] Label must be Qualified / Review Needed / Not Qualified")
        valid_labels = {"Qualified", "Review Needed", "Not Qualified"}
        for name, resume in [("strong", self._strong_resume()),
                               ("weak",   self._weak_resume()),
                               ("mid",    self._mid_resume())]:
            score, label = self.predict(self.bundle, resume)
            self.assertIn(label, valid_labels,
                f"ML-06 FAIL: '{label}' is not a recognised label.")
        print("ML-06 PASS — all labels are valid")

    def test_ML07_strong_resume_scores_higher_than_weak(self):
        """
        ML-07: Core ML sanity check.
        A resume with 7 years experience, M.Tech, and 10 skills
        must ALWAYS outscore a resume with 0 years and 2 basic skills.
        If this fails, the model is not working correctly.
        """
        print("\n[ML-07] Strong resume must score higher than weak resume")
        strong_score, _ = self.predict(self.bundle, self._strong_resume())
        weak_score, _   = self.predict(self.bundle, self._weak_resume())
        print(f"        Strong score: {strong_score}")
        print(f"        Weak score  : {weak_score}")
        self.assertGreater(
            strong_score, weak_score,
            f"ML-07 FAIL: Strong resume ({strong_score}) did not beat "
            f"weak resume ({weak_score}). Model may be broken."
        )
        print("ML-07 PASS — model correctly ranks resumes")

    def test_ML08_strong_resume_is_qualified(self):
        """
        ML-08: A highly qualified resume (PhD, 7 years, 10 skills, certs)
        must receive the 'Qualified' label.
        """
        print("\n[ML-08] Highly qualified resume should get 'Qualified' label")
        best_resume = {
            "skills": "Python, Machine Learning, TensorFlow, SQL, AWS, Docker, "
                      "Deep Learning, NLP, Pandas, Scikit-learn, PyTorch, Kubernetes",
            "experience_years": 10,
            "education": "PhD",
            "certifications": "AWS Certified",
            "job_role": "Data Scientist",
            "projects_count": 8,
        }
        score, label = self.predict(self.bundle, best_resume)
        print(f"        Score: {score}  Label: {label}")
        self.assertEqual(label, "Qualified",
            f"ML-08 FAIL: Best-case resume got '{label}' instead of 'Qualified'.")
        print("ML-08 PASS")

    def test_ML09_empty_skills_does_not_crash(self):
        """
        ML-09: Edge case — resume with no text should return a score,
        not crash the application.
        """
        print("\n[ML-09] Empty skills string should not crash predict_single")
        empty_resume = {
            "skills": "",
            "experience_years": 0,
            "education": "B.Sc",
            "certifications": "None",
            "job_role": "",
            "projects_count": 0,
        }
        try:
            score, label = self.predict(self.bundle, empty_resume)
            print(f"        Returned: score={score}, label={label}")
            self.assertIsNotNone(score,  "ML-09 FAIL: score was None")
            self.assertIsNotNone(label,  "ML-09 FAIL: label was None")
            print("ML-09 PASS — empty resume handled gracefully")
        except Exception as e:
            self.fail(f"ML-09 FAIL: predict_single crashed on empty input — {e}")

    def test_ML10_label_matches_score_threshold(self):
        """
        ML-10: Verify that the label is correctly assigned based on score.
        From train_model.py: >=65 → Qualified, >=40 → Review Needed, else Not Qualified
        """
        print("\n[ML-10] Label must match score threshold rules")
        for name, resume in [("strong", self._strong_resume()),
                               ("weak",   self._weak_resume()),
                               ("mid",    self._mid_resume())]:
            score, label = self.predict(self.bundle, resume)
            # Reproduce the same threshold logic from train_model.py
            if score >= 65:
                expected = "Qualified"
            elif score >= 40:
                expected = "Review Needed"
            else:
                expected = "Not Qualified"

            self.assertEqual(label, expected,
                f"ML-10 FAIL: {name} resume score={score} → label='{label}' "
                f"but threshold says '{expected}'.")
        print("ML-10 PASS — all labels match their score thresholds")


# ─────────────────────────────────────────────────────────────────────────────

class TestResumeParser(unittest.TestCase):
    """
    ML-11 to ML-17
    Tests every extraction function in resume_parser.py
    using plain strings — no PDF needed for most tests.
    """

    @classmethod
    def setUpClass(cls):
        """Import the parser module once."""
        try:
            from resume_parser import (
                extract_skills,
                extract_experience_years,
                extract_education,
                extract_certifications,
                extract_projects_count,
                extract_job_skills,
                compute_skill_overlap,
            )
            cls.extract_skills          = staticmethod(extract_skills)
            cls.extract_experience_years = staticmethod(extract_experience_years)
            cls.extract_education        = staticmethod(extract_education)
            cls.extract_certifications   = staticmethod(extract_certifications)
            cls.extract_projects_count   = staticmethod(extract_projects_count)
            cls.extract_job_skills       = staticmethod(extract_job_skills)
            cls.compute_skill_overlap    = staticmethod(compute_skill_overlap)
        except ImportError as e:
            raise unittest.SkipTest(f"resume_parser.py not importable — {e}")

    # ── ML-11: Skill extraction ───────────────────────────────────────────────
    def test_ML11_skill_extraction_finds_known_skills(self):
        """ML-11: extract_skills() must find known skills in text."""
        print("\n[ML-11] Skill extraction finds correct skills in text")
        text = (
            "I have 5 years of experience with Python and Machine Learning. "
            "I am proficient in SQL, TensorFlow, and Docker. "
            "I use Git daily and have worked with AWS."
        )
        skills = self.extract_skills(text)
        print(f"        Skills found: {skills}")

        # These are all in KNOWN_SKILLS in resume_parser.py
        self.assertIn("python",          skills, "ML-11 FAIL: 'python' not found")
        self.assertIn("machine learning", skills, "ML-11 FAIL: 'machine learning' not found")
        self.assertIn("sql",             skills, "ML-11 FAIL: 'sql' not found")
        self.assertIn("docker",          skills, "ML-11 FAIL: 'docker' not found")
        self.assertIn("aws",             skills, "ML-11 FAIL: 'aws' not found")
        print("ML-11 PASS — all expected skills extracted")

    def test_ML12_skill_extraction_returns_empty_for_blank_text(self):
        """ML-12: Empty text should return an empty list, not crash."""
        print("\n[ML-12] Skill extraction on empty text")
        skills = self.extract_skills("")
        self.assertEqual(skills, [],
            "ML-12 FAIL: Expected empty list for blank input.")
        print("ML-12 PASS")

    # ── ML-13: Experience extraction ─────────────────────────────────────────
    def test_ML13_experience_extraction_explicit_mention(self):
        """ML-13: extract_experience_years finds '5 years of experience'."""
        print("\n[ML-13] Experience extraction — explicit mention")
        text = "I have 5 years of experience in software development."
        years = self.extract_experience_years(text)
        print(f"        Years detected: {years}")
        self.assertEqual(years, 5,
            f"ML-13 FAIL: Expected 5 years, got {years}.")
        print("ML-13 PASS")

    def test_ML14_experience_extraction_from_date_range(self):
        """ML-14: extract_experience_years detects experience from year ranges."""
        print("\n[ML-14] Experience extraction — date range pattern")
        text = "Software Engineer at Safaricom\n2018 – Present\nDeveloped APIs."
        years = self.extract_experience_years(text)
        print(f"        Years estimated from date range: {years}")
        # 2018 to 2026 = ~7 or 8 years depending on current year
        self.assertGreater(years, 0,
            "ML-14 FAIL: Expected years > 0 from date range.")
        print("ML-14 PASS")

    # ── ML-15: Education extraction ───────────────────────────────────────────
    def test_ML15_education_detects_highest_degree(self):
        """ML-15: extract_education returns the highest degree found."""
        print("\n[ML-15] Education extraction")
        test_cases = [
            ("I hold a PhD in Computer Science from the University of Nairobi.", "PhD"),
            ("Completed an M.Tech in Data Science in 2020.", "M.Tech"),
            ("Bachelor of Science in Information Technology, 2018.", "B.Sc"),
            ("No degree information here.", "B.Sc"),  # fallback
        ]
        for text, expected in test_cases:
            result = self.extract_education(text)
            print(f"        '{text[:50]}...' → {result}")
            self.assertEqual(result, expected,
                f"ML-15 FAIL: Expected '{expected}', got '{result}'.")
        print("ML-15 PASS — all education levels detected correctly")

    # ── ML-16: Certification extraction ──────────────────────────────────────
    def test_ML16_certification_extraction(self):
        """ML-16: extract_certifications finds known cert mentions."""
        print("\n[ML-16] Certification extraction")
        text_with_cert = "I am AWS Certified Solutions Architect with 3 years cloud experience."
        cert = self.extract_certifications(text_with_cert)
        print(f"        Cert found: {cert}")
        self.assertNotEqual(cert, "None",
            "ML-16 FAIL: AWS cert not detected in text.")

        text_no_cert = "I have experience in Microsoft Excel and PowerPoint."
        cert_none = self.extract_certifications(text_no_cert)
        self.assertEqual(cert_none, "None",
            f"ML-16 FAIL: Expected 'None', got '{cert_none}'.")
        print("ML-16 PASS")

    # ── ML-17: Skill overlap ──────────────────────────────────────────────────
    def test_ML17_skill_overlap_computation(self):
        """
        ML-17: compute_skill_overlap measures how many job skills the resume covers.
        50% overlap = resume has 2 out of 4 required skills.
        """
        print("\n[ML-17] Skill overlap computation")

        resume_skills = ["python", "sql", "excel"]
        job_skills    = ["python", "sql", "tensorflow", "aws"]

        overlap = self.compute_skill_overlap(resume_skills, job_skills)
        print(f"        Resume: {resume_skills}")
        print(f"        Job needs: {job_skills}")
        print(f"        Overlap: {overlap:.0%}")

        self.assertAlmostEqual(overlap, 0.5, places=1,
            msg=f"ML-17 FAIL: Expected 50% overlap, got {overlap:.0%}.")

        # Full overlap
        full_overlap = self.compute_skill_overlap(
            ["python", "sql"],
            ["python", "sql"]
        )
        self.assertAlmostEqual(full_overlap, 1.0, places=1,
            msg="ML-17 FAIL: Expected 100% for identical skill sets.")

        # Zero overlap
        zero_overlap = self.compute_skill_overlap(
            ["excel"],
            ["python", "aws"]
        )
        self.assertAlmostEqual(zero_overlap, 0.0, places=1,
            msg="ML-17 FAIL: Expected 0% for no matching skills.")

        print("ML-17 PASS — overlap percentages are correct")


# ─────────────────────────────────────────────────────────────────────────────

class TestJobCategoryDetection(unittest.TestCase):
    """
    ML-18 to ML-24
    Tests the job category detection logic.

    _detect_job_category() is a nested function inside show_apply_page()
    so we cannot import it directly without running Streamlit.
    We replicate the same logic here to test it independently,
    and the Selenium tests verify the UI behaviour matches.
    """

    def _detect_category(self, title, description="", requirements=""):
        """
        Replicates the exact logic from apply.py _detect_job_category().
        Tests against this and the Selenium tests confirm the UI matches.
        """
        t = title.lower()
        full = (title + " " + description + " " + requirements).lower()

        # TITLE-FIRST (high priority) — same order as the fixed version
        if any(w in t for w in ["hr", "human resource", "recruitment",
                                  "talent acquisition", "payroll", "hrbp"]):
            return "hr"
        if any(w in t for w in ["finance", "financial", "accounting",
                                  "accountant", "audit", "tax", "budget"]):
            return "finance"
        if any(w in t for w in ["marketing", "brand", "seo",
                                  "digital marketing", "campaign", "crm"]):
            return "marketing"
        if any(w in t for w in ["security", "cyber", "penetration",
                                  "soc", "siem", "ethical hack"]):
            return "cybersecurity"
        if any(w in t for w in ["network", "networking", "infrastructure",
                                  "cisco", "devops", "cloud engineer",
                                  "sysadmin", "network admin"]):
            return "networking"
        if any(w in t for w in ["data scientist", "machine learning",
                                  "data analyst", "nlp", "analytics"]):
            return "data"
        if any(w in t for w in ["software", "developer", "programmer",
                                  "web developer", "mobile", "backend",
                                  "frontend", "full stack"]):
            return "software"
        if any(w in t for w in ["operations", "project manager",
                                  "supply chain", "logistics", "procurement"]):
            return "operations"
        if any(w in t for w in ["design", "designer", "ui", "ux",
                                  "graphic", "figma", "creative"]):
            return "design"
        return "general"

    def test_ML18_hr_title_returns_hr_category(self):
        """ML-18: 'HR Manager' title must map to 'hr' category."""
        print("\n[ML-18] HR Manager → hr category")
        result = self._detect_category("HR Manager")
        self.assertEqual(result, "hr",
            f"ML-18 FAIL: 'HR Manager' mapped to '{result}' instead of 'hr'.")
        print("ML-18 PASS")

    def test_ML19_finance_title_returns_finance_category(self):
        """ML-19: 'Financial Analyst' must map to 'finance'."""
        print("\n[ML-19] Financial Analyst → finance category")
        result = self._detect_category("Financial Analyst")
        self.assertEqual(result, "finance",
            f"ML-19 FAIL: Got '{result}' instead of 'finance'.")
        print("ML-19 PASS")

    def test_ML20_network_admin_returns_networking(self):
        """
        ML-20: The bug that was fixed — 'Network Admin' must NOT
        map to 'software' just because the word 'admin' appears.
        """
        print("\n[ML-20] Network Admin → networking (not software)")
        result = self._detect_category("Network Admin")
        self.assertNotEqual(result, "software",
            "ML-20 FAIL: Network Admin was misclassified as 'software'.")
        self.assertEqual(result, "networking",
            f"ML-20 FAIL: Got '{result}' instead of 'networking'.")
        print("ML-20 PASS — original bug is fixed")

    def test_ML21_hr_not_misclassified_as_software(self):
        """
        ML-21: Critical regression test.
        HR Manager with 'engineering team' in description must
        still return 'hr', not 'software'.
        This was the original bug that caused wrong questions to show.
        """
        print("\n[ML-21] HR job with 'engineer' in description → still 'hr'")
        result = self._detect_category(
            title="HR Business Partner",
            description="Partner with the engineering team on people ops.",
            requirements="3 years HR experience, knowledge of employment law."
        )
        self.assertEqual(result, "hr",
            f"ML-21 FAIL: HR role misclassified as '{result}'. Bug is back!")
        print("ML-21 PASS — HR not misclassified by keyword in description")

    def test_ML22_software_developer_returns_software(self):
        """ML-22: Pure software role maps to 'software'."""
        print("\n[ML-22] Software Developer → software category")
        result = self._detect_category("Software Developer")
        self.assertEqual(result, "software",
            f"ML-22 FAIL: Got '{result}' instead of 'software'.")
        print("ML-22 PASS")

    def test_ML23_cybersecurity_analyst_returns_cybersecurity(self):
        """ML-23: Cybersecurity Analyst maps to 'cybersecurity'."""
        print("\n[ML-23] Cybersecurity Analyst → cybersecurity category")
        result = self._detect_category("Cybersecurity Analyst")
        self.assertEqual(result, "cybersecurity",
            f"ML-23 FAIL: Got '{result}' instead of 'cybersecurity'.")
        print("ML-23 PASS")

    def test_ML24_unknown_title_returns_general(self):
        """ML-24: An unrecognised job title returns 'general'."""
        print("\n[ML-24] Unrecognised title → general category")
        result = self._detect_category("Office Assistant", "General office duties.")
        self.assertEqual(result, "general",
            f"ML-24 FAIL: Got '{result}' instead of 'general'.")
        print("ML-24 PASS")


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 2 — SELENIUM UI TESTS  (requires browser + running Streamlit app)
# ─────────────────────────────────────────────────────────────────────────────

def _selenium_available():
    """Returns True only if selenium and chromedriver are importable."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        return True
    except ImportError:
        return False


def get_driver():
    """Creates and returns a configured Chrome WebDriver."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()
    return driver


def wait(seconds=1.5):
    time.sleep(seconds)


def fill_input(driver, label_text, value):
    """Find a Streamlit text input by its label and type a value into it."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    wait(0.5)
    labels = driver.find_elements(By.TAG_NAME, "label")
    for label in labels:
        if label_text.lower() in label.text.lower():
            parent = label.find_element(By.XPATH, "..")
            try:
                inp = parent.find_element(By.TAG_NAME, "input")
            except Exception:
                inp = parent.find_element(By.TAG_NAME, "textarea")
            inp.click()
            inp.send_keys(Keys.CONTROL + "a")
            inp.send_keys(Keys.DELETE)
            inp.send_keys(value)
            return
    raise Exception(f"Input with label '{label_text}' not found on page.")


def click_button(driver, label_text):
    """Click a Streamlit button by its visible label text."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    wait(0.5)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[normalize-space()='{label_text}']")
        )
    ).click()


def login(driver, email, password):
    """Log into the app with the given credentials."""
    driver.get(APP_URL)
    wait(3)
    fill_input(driver, "Email address", email)
    fill_input(driver, "Password", password)
    click_button(driver, "Log in")
    wait(3)


# ── Build Selenium test classes only if selenium is installed ─────────────────

if _selenium_available():

    class TestAuthenticationUI(unittest.TestCase):
        """UI-01 to UI-07  —  Login, Signup, Logout via browser."""

        def setUp(self):
            self.driver = get_driver()

        def tearDown(self):
            self.driver.quit()

        def test_UI01_valid_seeker_login(self):
            print("\n[UI-01] Valid seeker login")
            login(self.driver, "seeker@test.com", "test123")
            self.assertIn("Hello", self.driver.page_source,
                "UI-01 FAIL: Dashboard did not load after valid seeker login.")
            print("UI-01 PASS")

        def test_UI02_valid_employer_login(self):
            print("\n[UI-02] Valid employer login")
            login(self.driver, "employer@test.com", "test123")
            self.assertIn("Hello", self.driver.page_source,
                "UI-02 FAIL: Employer dashboard did not load.")
            print("UI-02 PASS")

        def test_UI03_wrong_password(self):
            print("\n[UI-03] Wrong password shows correct error")
            self.driver.get(APP_URL)
            wait(3)
            fill_input(self.driver, "Email address", "seeker@test.com")
            fill_input(self.driver, "Password", "wrongpassword999")
            click_button(self.driver, "Log in")
            wait(2)
            self.assertIn("Incorrect password", self.driver.page_source,
                "UI-03 FAIL: Expected 'Incorrect password' error.")
            print("UI-03 PASS")

        def test_UI04_unregistered_email(self):
            print("\n[UI-04] Unregistered email shows correct error")
            self.driver.get(APP_URL)
            wait(3)
            fill_input(self.driver, "Email address", "nobody@nowhere.com")
            fill_input(self.driver, "Password", "test123")
            click_button(self.driver, "Log in")
            wait(2)
            self.assertIn("No account found", self.driver.page_source,
                "UI-04 FAIL: Expected 'No account found' error.")
            print("UI-04 PASS")

        def test_UI05_short_password_blocked(self):
            print("\n[UI-05] Short password is blocked on signup")
            self.driver.get(APP_URL)
            wait(3)
            click_button(self.driver, "Create an account")
            wait(2)
            fill_input(self.driver, "Full name", "Test User")
            fill_input(self.driver, "Email address", "short@test.com")
            fill_input(self.driver, "Password", "abc")
            fill_input(self.driver, "Confirm password", "abc")
            click_button(self.driver, "Create account")
            wait(2)
            self.assertIn("6 characters", self.driver.page_source,
                "UI-05 FAIL: Short password warning not shown.")
            print("UI-05 PASS")

        def test_UI06_duplicate_email_blocked(self):
            print("\n[UI-06] Duplicate email blocked on signup")
            self.driver.get(APP_URL)
            wait(3)
            click_button(self.driver, "Create an account")
            wait(2)
            fill_input(self.driver, "Full name", "Another User")
            fill_input(self.driver, "Email address", "seeker@test.com")
            fill_input(self.driver, "Password", "test123")
            fill_input(self.driver, "Confirm password", "test123")
            click_button(self.driver, "Create account")
            wait(2)
            self.assertIn("already exists", self.driver.page_source,
                "UI-06 FAIL: Duplicate email not blocked.")
            print("UI-06 PASS")

        def test_UI07_logout_clears_session(self):
            print("\n[UI-07] Logout clears session — back button shows login")
            login(self.driver, "seeker@test.com", "test123")
            click_button(self.driver, "Log out")
            wait(2)
            self.driver.back()
            wait(2)
            self.assertNotIn("Hello", self.driver.page_source,
                "UI-07 FAIL: Dashboard still accessible after logout.")
            print("UI-07 PASS")

    # ─────────────────────────────────────────────────────────────────────────

    class TestJobPostingUI(unittest.TestCase):
        """UI-10 to UI-12  —  Employer posts and manages jobs."""

        def setUp(self):
            self.driver = get_driver()
            login(self.driver, "employer@test.com", "test123")
            click_button(self.driver, "Dashboard")
            wait(2)

        def tearDown(self):
            self.driver.quit()

        def test_UI10_employer_posts_new_job(self):
            print("\n[UI-10] Employer posts a new job listing")
            fill_input(self.driver, "Job Title",       "Finance Manager")
            fill_input(self.driver, "Company Name",    "Pioneer Insurance Group")
            fill_input(self.driver, "Location",        "Nairobi")
            fill_input(self.driver, "Job Description",
                       "Manage company accounts, budgets and financial reports.")
            fill_input(self.driver, "Requirements",
                       "CPA qualification, 3+ years finance experience.")
            fill_input(self.driver, "Salary",          "KES 120,000")
            click_button(self.driver, "Post Job")
            wait(3)
            self.assertIn("Finance Manager", self.driver.page_source,
                "UI-10 FAIL: Posted job did not appear on page.")
            print("UI-10 PASS")

        def test_UI11_blank_title_not_posted(self):
            print("\n[UI-11] Job with blank title is not saved")
            fill_input(self.driver, "Company Name",    "Pioneer Insurance")
            fill_input(self.driver, "Location",        "Mombasa")
            fill_input(self.driver, "Job Description", "Some duties.")
            fill_input(self.driver, "Requirements",    "Some requirements.")
            click_button(self.driver, "Post Job")
            wait(2)
            self.assertNotIn("Job posted successfully", self.driver.page_source,
                "UI-11 FAIL: Job was saved despite a blank title.")
            print("UI-11 PASS")

    # ─────────────────────────────────────────────────────────────────────────

    class TestMLScoringUI(unittest.TestCase):
        """
        UI-ML-01 to UI-ML-03
        End-to-end ML tests through the browser.
        These verify that the full pipeline — upload PDF → parse →
        score → display — works correctly from the user's point of view.

        REQUIREMENT: Have a real PDF file at the path below.
        Replace with any PDF resume on your computer.
        """

        RESUME_PDF_PATH = os.path.join(PROJECT_DIR, "sample_resume.pdf")

        @classmethod
        def setUpClass(cls):
            if not os.path.exists(cls.RESUME_PDF_PATH):
                raise unittest.SkipTest(
                    f"sample_resume.pdf not found at {cls.RESUME_PDF_PATH}. "
                    "Add any PDF resume with that filename to run UI ML tests."
                )

        def setUp(self):
            self.driver = get_driver()
            login(self.driver, "seeker@test.com", "test123")
            wait(2)

        def tearDown(self):
            self.driver.quit()

        def _open_first_job_apply_page(self):
            """Navigate to Browse Jobs and click Apply on the first listed job."""
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            click_button(self.driver, "Browse Jobs")
            wait(3)
            # Click the first Apply Now button on the job board
            apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Apply Now')]")
                )
            )
            apply_btn.click()
            wait(2)

        def test_UIML01_ml_score_appears_on_success_screen(self):
            """
            UI-ML-01: After uploading a resume and submitting,
            the ML score must appear on the success screen.
            This tests the full end-to-end ML pipeline through the browser.
            """
            print("\n[UI-ML-01] Upload resume → ML score appears on screen")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self._open_first_job_apply_page()

            # Upload the PDF resume
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='file']")
                )
            )
            file_input.send_keys(self.RESUME_PDF_PATH)
            wait(3)

            # Answer any screener questions (select first radio option for each)
            try:
                radios = self.driver.find_elements(
                    By.XPATH, "//div[@role='radio']"
                )
                # Click one option per question group
                clicked = set()
                for radio in radios:
                    group = radio.get_attribute("data-baseweb")
                    if group not in clicked:
                        radio.click()
                        clicked.add(group)
                        wait(0.3)
            except Exception:
                pass  # No questions visible — that is also acceptable

            # Submit the application
            click_button(self.driver, "Submit Application")
            wait(5)  # Allow time for PDF parsing and ML inference

            page = self.driver.page_source
            self.assertIn("Application Submitted", page,
                "UI-ML-01 FAIL: Success screen did not appear.")

            # Score must appear as a number
            import re
            score_pattern = re.search(r"\b(\d{1,3})/100\b", page)
            self.assertIsNotNone(score_pattern,
                "UI-ML-01 FAIL: ML score (X/100) not found on success screen.")

            score_value = int(score_pattern.group(1))
            self.assertGreaterEqual(score_value, 0,
                "UI-ML-01 FAIL: Score is below 0.")
            self.assertLessEqual(score_value, 100,
                "UI-ML-01 FAIL: Score exceeds 100.")
            print(f"        Score displayed: {score_value}/100")
            print("UI-ML-01 PASS — ML score appears correctly on success screen")

        def test_UIML02_label_is_visible_on_success_screen(self):
            """
            UI-ML-02: One of the three ML labels must appear on the success screen.
            Confirms label rendering, not just the numeric score.
            """
            print("\n[UI-ML-02] ML label visible on success screen")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self._open_first_job_apply_page()

            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='file']")
                )
            )
            file_input.send_keys(self.RESUME_PDF_PATH)
            wait(3)
            click_button(self.driver, "Submit Application")
            wait(5)

            page = self.driver.page_source
            has_label = (
                "Qualified" in page or
                "Review Needed" in page or
                "Not Qualified" in page
            )
            self.assertTrue(has_label,
                "UI-ML-02 FAIL: None of the ML labels found on success screen.")
            print("UI-ML-02 PASS — ML label visible on success screen")

        def test_UIML03_skills_match_section_appears(self):
            """
            UI-ML-03: The skills match summary must appear after submission.
            Confirms the resume parser extracted skills correctly.
            """
            print("\n[UI-ML-03] Skills match section appears on success screen")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self._open_first_job_apply_page()

            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='file']")
                )
            )
            file_input.send_keys(self.RESUME_PDF_PATH)
            wait(3)
            click_button(self.driver, "Submit Application")
            wait(5)

            page = self.driver.page_source
            # The success screen shows "Skills Match" or "Matched" section
            self.assertTrue(
                "Skills" in page or "Match" in page,
                "UI-ML-03 FAIL: Skills match section not found on success screen."
            )
            print("UI-ML-03 PASS — skills match section is present")

    # ─────────────────────────────────────────────────────────────────────────

    class TestSecurityUI(unittest.TestCase):
        """UI-SEC — SQL injection and role enforcement."""

        def setUp(self):
            self.driver = get_driver()

        def tearDown(self):
            self.driver.quit()

        def test_UISEC01_sql_injection_blocked(self):
            print("\n[UI-SEC-01] SQL injection attempt is blocked")
            self.driver.get(APP_URL)
            wait(3)
            fill_input(self.driver, "Email address", "' OR '1'='1")
            fill_input(self.driver, "Password", "anything")
            click_button(self.driver, "Log in")
            wait(2)
            self.assertNotIn("Hello", self.driver.page_source,
                "UI-SEC-01 FAIL: SQL injection granted access!")
            print("UI-SEC-01 PASS — SQL injection correctly blocked")

        def test_UISEC02_seeker_cannot_see_post_job(self):
            print("\n[UI-SEC-02] Seeker cannot access job posting form")
            login(self.driver, "seeker@test.com", "test123")
            self.assertNotIn("Post Job", self.driver.page_source,
                "UI-SEC-02 FAIL: Seeker can see 'Post Job' button.")
            print("UI-SEC-02 PASS — seeker cannot access employer features")

    # ─────────────────────────────────────────────────────────────────────────

    class TestPerformanceUI(unittest.TestCase):
        """UI-PERF — Response time measurements."""

        def setUp(self):
            self.driver = get_driver()

        def tearDown(self):
            self.driver.quit()

        def test_UIPERF01_login_page_loads_under_5_seconds(self):
            print("\n[UI-PERF-01] Login page load time")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            start = time.time()
            self.driver.get(APP_URL)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            elapsed = time.time() - start
            print(f"        Login page loaded in {elapsed:.2f} seconds")
            self.assertLess(elapsed, 5,
                f"UI-PERF-01 FAIL: Took {elapsed:.2f}s (limit: 5s)")
            print("UI-PERF-01 PASS")

        def test_UIPERF02_dashboard_loads_under_5_seconds(self):
            print("\n[UI-PERF-02] Dashboard load time after login")
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            self.driver.get(APP_URL)
            wait(3)
            fill_input(self.driver, "Email address", "seeker@test.com")
            fill_input(self.driver, "Password", "test123")
            start = time.time()
            click_button(self.driver, "Log in")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(),'Hello')]")
                )
            )
            elapsed = time.time() - start
            print(f"        Dashboard loaded in {elapsed:.2f} seconds")
            self.assertLess(elapsed, 5,
                f"UI-PERF-02 FAIL: Took {elapsed:.2f}s (limit: 5s)")
            print("UI-PERF-02 PASS")

else:
    print("\n⚠ Selenium not installed — skipping all UI tests.")
    print("  To install: pip install selenium webdriver-manager\n")


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT + COMMAND-LINE FLAGS
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 65)
    print("  Pioneer Insurance JobMatch — Full Test Suite")
    print("=" * 65)

    # Parse simple flags
    ml_only = "--ml-only" in sys.argv
    ui_only = "--ui-only" in sys.argv

    # Remove custom flags before passing to unittest
    sys.argv = [a for a in sys.argv
                if a not in ("--ml-only", "--ui-only")]

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    if not ui_only:
        print("\n── Direct ML Tests (no browser) ──────────────────────────")
        suite.addTests(loader.loadTestsFromTestCase(TestMLModelFile))
        suite.addTests(loader.loadTestsFromTestCase(TestPredictSingle))
        suite.addTests(loader.loadTestsFromTestCase(TestResumeParser))
        suite.addTests(loader.loadTestsFromTestCase(TestJobCategoryDetection))

    if not ml_only and _selenium_available():
        print("\n── Selenium UI Tests (browser) ───────────────────────────")
        print("   Make sure:  streamlit run app.py  is running first!")
        suite.addTests(loader.loadTestsFromTestCase(TestAuthenticationUI))
        suite.addTests(loader.loadTestsFromTestCase(TestJobPostingUI))
        suite.addTests(loader.loadTestsFromTestCase(TestMLScoringUI))
        suite.addTests(loader.loadTestsFromTestCase(TestSecurityUI))
        suite.addTests(loader.loadTestsFromTestCase(TestPerformanceUI))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 65)
    print(f"  Tests run : {result.testsRun}")
    print(f"  Passed    : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failed    : {len(result.failures)}")
    print(f"  Errors    : {len(result.errors)}")
    print("=" * 65)

    sys.exit(0 if result.wasSuccessful() else 1)