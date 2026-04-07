"""
email.utils.py - Email Notification system
======================================================
Sends approval and rejection emails to job seekers
When an employer makes a decision on their application

SETUP INSTRUCTION
======================================================
- Option 1: Gmail
1. Go to your Google Account → Security → 2-Step Verification (enable it)
2. Then go to Security → App Passwords
3. Generate an App Password for "Mail"
4. Copy the 16-character password (e.g. "abcd efgh ijkl mnop")
5. Fill in the config below:
      EMAIL_PROVIDER = "gmail"
      SENDER_EMAIL = "yourname@gmail.com"
      SENDER_PASSWORD = "abcdefghijklmnop" ← the app password, no spaces

── OPTION 2: Outlook / Office365 (for Pioneer Insurance Group) ────────────
1. Use your company email address and password
2. If MFA is enabled, ask IT for an App Password
3. Fill in the config below:
      EMAIL_PROVIDER = "outlook"
      SENDER_EMAIL = "yourname@pioneerinsurance.co.ke"
      SENDER_PASSWORD = "your_password_here"

── OPTION 3: SendGrid API (most professional, free tier = 100 emails/day) ─
1. Sign up at sendgrid.com
2. Create an API key (Settings → API Keys → Create)
3. Fill in:
      EMAIL_PROVIDER = "sendgrid"
      SENDER_EMAIL = "yourname@pioneerinsurance.co.ke"
      SENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxxx"

SECURITY NOTE:
  Never hardcode passwords in production code.
  Move these to a .env file and use python-dotenv to load them.
  We show them inline here for simplicity during development.
  Add .env to your .gitignore so it's never committed to GitHub.

INSTALL:
  pip install python-dotenv   ← for .env file support (recommended)
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email Configuration

EMAIL_PROVIDER = "gmail"  # <- gmail| outlook| sendgrid
SENDER_EMAIL = "migelbrian3@gmail.com"  # <- sending email
SENDER_PASSWORD = "app_password"  # <- Not the login pasSword

SENDGRID_API_KEY = ""  # <-Only used when needed

# smtp settings per provider - no need to change these
SMTP_SETTINGS = {
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
    },
    "outlook": {
        "host": "smtp.office365.com",
        "port": 587,
    },
}

# Company branding - appears in email headers and footer
COMPANY_NAME = "Pioneer Insurance Group"
COMPANY_EMAIL = SENDER_EMAIL
COMPANY_WEBSITE = "https://www.pioneerinsurance.co.ke"


# Core Email Sender

def send_email(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """
    Sends an HTML email using the configured provider
    
    recipient: recipient email address
    subject: email subject line
    html_body: full HTML content of the email

    Returns (Success: bool, message: str)

    How smtp works:
        1. We create a secure SSL/TLS connection to the mail server
        2. we log in with our sender credentials
        3. we hand off the message to the server
        4. The server delivers it to the recipient
    The whole happens in 1-2 seconds
    """
    if EMAIL_PROVIDER == "sendgrid":
        return _send_via_sendgrid(to_email, subject, html_body)

    # ─ Build the email message
    # object ───────────────────────────────────────
    # MIMEMultipart("alternative") means the email has both plain text
    # and HTML versions — mail clients show whichever they support.

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{COMPANY_NAME} <{SENDER_EMAIL}"
    message["To"] = to_email

    # Plain text fallback or email clients that don't render HTML
    plain_text = (
        f"{subject}\n\n"
        f"Please view this email in an HTML-capable email client.\n\n"
        f"{COMPANY_NAME}"
    )

    message.attach(MIMEText(plain_text, "plain"))
    message.attach(MIMEText(html_body, "html"))






def _send_via_sendgrid(to_email, subject, html_body):
    pass