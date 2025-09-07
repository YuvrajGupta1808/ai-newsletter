import os
import secrets

# SECURITY: All sensitive data moved to environment variables
# No fallback values for production secrets
NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY")
GMAIL_USER   = os.getenv("GMAIL_USER")
GMAIL_PASS   = os.getenv("GMAIL_PASS")   # Gmail App Password
SHEET_ID     = os.getenv("GOOGLE_SHEET_ID")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON_PATH", "credentials.json")
FLASK_SECRET = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# Validate required environment variables
required_vars = {
    "NEWSAPI_KEY": NEWSAPI_KEY,
    "GMAIL_USER": GMAIL_USER, 
    "GMAIL_PASS": GMAIL_PASS,
    "GOOGLE_SHEET_ID": SHEET_ID
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Must match checkbox values in index.html
TOPICS = ["Technology", "Sports", "Politics", "Finance"]

# Desired headers in the sheet (no Name)
# Extended for verification and OTP flow
DESIRED_HEADERS = [
    "Email",
    "Technology",
    "Sports",
    "Politics",
    "Finance",
    "Max_items",
    "Timestamp",
    "Verified",
    "OTP_Code",
    "OTP_Expires",
]