# test_jobmatch.py
# ─────────────────────────────────────────────────────────
# Selenium test suite for the Pioneer Insurance JobMatch System
# Make sure "streamlit run app.py" is running before executing this.
#
# Run with:   python test_jobmatch.py
# ─────────────────────────────────────────────────────────

import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

APP_URL = "http://localhost:8501"

# ── Helper: short wait for Streamlit to re-render ─────────────────────────────
def wait(seconds=1.5):
    time.sleep(seconds)

# ── Helper: type into a Streamlit text input by its label ─────────────────────
def fill_input(driver, label_text, value):
    """
    Streamlit renders inputs inside a <label>. We find the label, get the
    input that follows it, clear it, and type the new value.
    """
    wait(0.5)
    labels = driver.find_elements(By.TAG_NAME, "label")
    for label in labels:
        if label_text.lower() in label.text.lower():
            # The input/textarea is a sibling of the label's parent div
            parent = label.find_element(By.XPATH, "..")
            try:
                inp = parent.find_element(By.TAG_NAME, "input")
            except:
                inp = parent.find_element(By.TAG_NAME, "textarea")
            inp.click()
            inp.send_keys(Keys.CONTROL + "a")   # select all existing text
            inp.send_keys(Keys.DELETE)           # clear it
            inp.send_keys(value)                 # type the new value
            return
    raise Exception(f"Input with label '{label_text}' not found on page.")

# ── Helper: click a Streamlit button by its label text ───────────────────────
def click_button(driver, label_text):
    wait(0.5)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[normalize-space()='{label_text}']")
        )
    ).click()


# ═════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthentication(unittest.TestCase):
    """
    TC-01 to TC-07  —  Login, Signup, and Logout
    """

    def setUp(self):
        """Runs before every individual test — opens a fresh browser."""
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        self.driver.maximize_window()
        self.driver.get(APP_URL)
        wait(3)   # give Streamlit time to load fully

    def tearDown(self):
        """Runs after every individual test — closes the browser."""
        self.driver.quit()

    # ── TC-01: Valid seeker login ─────────────────────────────────────────────
    def test_TC01_valid_seeker_login(self):
        print("\n[TC-01] Valid seeker login")
        fill_input(self.driver, "Email address", "seeker@test.com")
        fill_input(self.driver, "Password", "test123")
        click_button(self.driver, "Log in")
        wait(3)

        # After login, the sidebar should show the user's name
        page_source = self.driver.page_source
        self.assertIn("Hello", page_source,
                      "TC-01 FAIL: Dashboard did not load after valid login.")
        print("TC-01 PASS")

    # ── TC-02: Valid employer login ───────────────────────────────────────────
    def test_TC02_valid_employer_login(self):
        print("\n[TC-02] Valid employer login")
        fill_input(self.driver, "Email address", "employer@test.com")
        fill_input(self.driver, "Password", "test123")
        click_button(self.driver, "Log in")
        wait(3)

        page_source = self.driver.page_source
        self.assertIn("Hello", page_source,
                      "TC-02 FAIL: Employer dashboard did not load.")
        print("TC-02 PASS")

    # ── TC-03: Wrong password ─────────────────────────────────────────────────
    def test_TC03_wrong_password(self):
        print("\n[TC-03] Wrong password")
        fill_input(self.driver, "Email address", "seeker@test.com")
        fill_input(self.driver, "Password", "wrongpassword")
        click_button(self.driver, "Log in")
        wait(2)

        page_source = self.driver.page_source
        self.assertIn("Incorrect password", page_source,
                      "TC-03 FAIL: Expected 'Incorrect password' error.")
        print("TC-03 PASS")

    # ── TC-04: Unregistered email ─────────────────────────────────────────────
    def test_TC04_unregistered_email(self):
        print("\n[TC-04] Unregistered email")
        fill_input(self.driver, "Email address", "nobody@nowhere.com")
        fill_input(self.driver, "Password", "test123")
        click_button(self.driver, "Log in")
        wait(2)

        page_source = self.driver.page_source
        self.assertIn("No account found", page_source,
                      "TC-04 FAIL: Expected 'No account found' error.")
        print("TC-04 PASS")

    # ── TC-05: Short password on signup ──────────────────────────────────────
    def test_TC05_short_password_signup(self):
        print("\n[TC-05] Short password on signup")
        click_button(self.driver, "Create an account")
        wait(2)

        fill_input(self.driver, "Full name", "Test User")
        fill_input(self.driver, "Email address", "short@test.com")
        fill_input(self.driver, "Password", "abc")        # only 3 chars
        fill_input(self.driver, "Confirm password", "abc")
        click_button(self.driver, "Create account")
        wait(2)

        page_source = self.driver.page_source
        self.assertIn("6 characters", page_source,
                      "TC-05 FAIL: Expected short password warning.")
        print("TC-05 PASS")

    # ── TC-06: Duplicate email ────────────────────────────────────────────────
    def test_TC06_duplicate_email_signup(self):
        print("\n[TC-06] Duplicate email signup")
        click_button(self.driver, "Create an account")
        wait(2)

        fill_input(self.driver, "Full name", "Duplicate User")
        fill_input(self.driver, "Email address", "seeker@test.com")  # already exists
        fill_input(self.driver, "Password", "test123")
        fill_input(self.driver, "Confirm password", "test123")
        click_button(self.driver, "Create account")
        wait(2)

        page_source = self.driver.page_source
        self.assertIn("already exists", page_source,
                      "TC-06 FAIL: Expected duplicate email error.")
        print("TC-06 PASS")


# ─────────────────────────────────────────────────────────────────────────────

class TestJobPosting(unittest.TestCase):
    """
    TC-10 to TC-12  —  Employer posts, edits, and deactivates jobs
    """

    def setUp(self):
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        self.driver.maximize_window()
        self.driver.get(APP_URL)
        wait(3)

        # Log in as employer before each test
        fill_input(self.driver, "Email address", "employer@test.com")
        fill_input(self.driver, "Password", "test123")
        click_button(self.driver, "Log in")
        wait(3)

        # Navigate to employer dashboard
        click_button(self.driver, "Dashboard")
        wait(2)

    def tearDown(self):
        self.driver.quit()

    # ── TC-10: Post a new job ─────────────────────────────────────────────────
    def test_TC10_post_new_job(self):
        print("\n[TC-10] Employer posts a new job")
        fill_input(self.driver, "Job Title",      "Finance Manager")
        fill_input(self.driver, "Company Name",   "Pioneer Insurance Group")
        fill_input(self.driver, "Location",       "Nairobi")
        fill_input(self.driver, "Job Description",
                   "Manage the company financial accounts and budgets.")
        fill_input(self.driver, "Requirements",
                   "CPA qualification, 3 years experience in finance.")
        fill_input(self.driver, "Salary",         "KES 120,000")
        click_button(self.driver, "Post Job")
        wait(3)

        page_source = self.driver.page_source
        self.assertIn("Finance Manager", page_source,
                      "TC-10 FAIL: New job did not appear after posting.")
        print("TC-10 PASS")

    # ── TC-11: Post job with blank title ─────────────────────────────────────
    def test_TC11_post_job_blank_title(self):
        print("\n[TC-11] Post job with blank title")
        # Leave title empty, fill everything else
        fill_input(self.driver, "Company Name",    "Pioneer Insurance Group")
        fill_input(self.driver, "Location",        "Nairobi")
        fill_input(self.driver, "Job Description", "Some description.")
        fill_input(self.driver, "Requirements",    "Some requirements.")
        click_button(self.driver, "Post Job")
        wait(2)

        page_source = self.driver.page_source
        # Should show a warning - job should NOT be saved
        self.assertNotIn("Job posted successfully", page_source,
                         "TC-11 FAIL: Job was saved despite empty title.")
        print("TC-11 PASS")


# ─────────────────────────────────────────────────────────────────────────────

class TestSecurity(unittest.TestCase):
    """
    TC-19  —  SQL injection attempt
    """

    def setUp(self):
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        self.driver.maximize_window()
        self.driver.get(APP_URL)
        wait(3)

    def tearDown(self):
        self.driver.quit()

    # ── TC-19: SQL injection ──────────────────────────────────────────────────
    def test_TC19_sql_injection(self):
        print("\n[TC-19] SQL injection attempt")
        fill_input(self.driver, "Email address", "' OR '1'='1")
        fill_input(self.driver, "Password", "anything")
        click_button(self.driver, "Log in")
        wait(2)

        page_source = self.driver.page_source
        # Must NOT be logged in — should see error, not a dashboard
        self.assertNotIn("Hello", page_source,
                         "TC-19 FAIL: SQL injection granted access!")
        self.assertIn("No account found", page_source,
                      "TC-19 FAIL: Expected login error for injection input.")
        print("TC-19 PASS")


# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance(unittest.TestCase):
    """
    Performance check — measures how long the login page and dashboard take.
    Uses Python's time module, no extra tools needed.
    """

    def setUp(self):
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        self.driver.maximize_window()

    def tearDown(self):
        self.driver.quit()

    def test_login_page_load_time(self):
        print("\n[PERF-01] Login page load time")
        start = time.time()
        self.driver.get(APP_URL)
        # Wait until the email input appears (page is ready)
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "input"))
        )
        elapsed = time.time() - start
        print(f"  Login page loaded in {elapsed:.2f} seconds")
        self.assertLess(elapsed, 5,
                        f"PERF-01 FAIL: Page took {elapsed:.2f}s (limit: 5s)")
        print("PERF-01 PASS")

    def test_dashboard_load_time(self):
        print("\n[PERF-02] Dashboard load after login")
        self.driver.get(APP_URL)
        wait(3)

        fill_input(self.driver, "Email address", "seeker@test.com")
        fill_input(self.driver, "Password", "test123")

        start = time.time()
        click_button(self.driver, "Log in")
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(text(),'Hello')]")
            )
        )
        elapsed = time.time() - start
        print(f"  Dashboard loaded in {elapsed:.2f} seconds after login")
        self.assertLess(elapsed, 5,
                        f"PERF-02 FAIL: Dashboard took {elapsed:.2f}s (limit: 5s)")
        print("PERF-02 PASS")


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Pioneer Insurance JobMatch — Selenium Test Suite")
    print("  Make sure:  streamlit run app.py  is running first!")
    print("=" * 60)
    unittest.main(verbosity=2)