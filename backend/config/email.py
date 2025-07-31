# Email Configuration for WayfareProject
import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail

# Load environment variables
load_dotenv()

# =============================================================================
# EMAIL CONFIGURATION OPTIONS
# =============================================================================

# Development configuration - No real email sending (Currently Active)
development_config = ConnectionConfig(
    MAIL_USERNAME="test@wayfareproject.com",
    MAIL_PASSWORD="test_password",
    MAIL_FROM="noreply@wayfareproject.com",
    MAIL_PORT=587,
    MAIL_SERVER="localhost",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    SUPPRESS_SEND=1  # This prevents actual email sending - perfect for development!
)

# Gmail configuration with app password (for production)
gmail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("GMAIL_USERNAME", "your_email@gmail.com"),
    MAIL_PASSWORD=os.getenv("GMAIL_APP_PASSWORD", "your_app_password"), 
    MAIL_FROM=os.getenv("GMAIL_FROM", "your_email@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Mailtrap configuration (perfect for development - catches all emails)
mailtrap_config = ConnectionConfig(
    MAIL_USERNAME="your_mailtrap_username",     # From Mailtrap inbox settings
    MAIL_PASSWORD="your_mailtrap_password",     # From Mailtrap inbox settings
    MAIL_FROM="test@wayfareproject.com",        # Can be any email for testing
    MAIL_PORT=2525,
    MAIL_SERVER="sandbox.smtp.mailtrap.io",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# =============================================================================
# ACTIVE CONFIGURATION
# =============================================================================
# Change this to switch between different email configurations
# Options: development_config, gmail_config, mailtrap_config

# STEP 1: Update gmail_config above with your Gmail credentials
# STEP 2: Change this line to: mail_config = gmail_config
# STEP 3: Restart your FastAPI server

mail_config = gmail_config  # Updated by setup script

# FastMail instance using the active configuration
fastmail = FastMail(mail_config)

# =============================================================================
# CONFIGURATION SWITCHING GUIDE
# =============================================================================
"""
To switch email configurations:

1. Development (no real emails):
   mail_config = development_config
   
2. Gmail (production):
   - Set up Gmail app password at: https://myaccount.google.com/apppasswords
   - Update gmail_config with your credentials
   - Set: mail_config = gmail_config
   
3. Mailtrap (development with email testing):
   - Sign up at: https://mailtrap.io/
   - Update mailtrap_config with your credentials
   - Set: mail_config = mailtrap_config
""" 