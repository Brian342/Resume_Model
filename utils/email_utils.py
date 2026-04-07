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

