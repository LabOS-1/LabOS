#!/usr/bin/env python3
"""
Quick script to get Gmail OAuth2 refresh token using console flow.
Run this locally: python scripts/get_gmail_token.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Your Gmail API credentials
CLIENT_ID = os.getenv('GMAIL_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET', '')

if not CLIENT_SECRET:
    print("❌ Please set GMAIL_CLIENT_SECRET environment variable first:")
    print("   export GMAIL_CLIENT_SECRET='your-client-secret'")
    print("\n   Find it in Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs")
    exit(1)

# Create OAuth flow with OOB (out-of-band) method
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(
    client_config,
    scopes=['https://www.googleapis.com/auth/gmail.send']
)

print("🔐 Opening browser for Gmail authorization...")
print()

# Use fixed port 8888
credentials = flow.run_local_server(
    port=8080,
    open_browser=True,
    success_message="Authorization complete! You can close this window."
)

print("\n" + "="*60)
print("✅ Authorization successful!")
print("="*60)
print(f"\nGMAIL_REFRESH_TOKEN={credentials.refresh_token}")
print(f"\nGMAIL_ACCESS_TOKEN={credentials.token}")
print("\n" + "="*60)
print("Copy the GMAIL_REFRESH_TOKEN above and update it in:")
print("  VM: ~/labos/backend/.env")
print("  Then restart: docker-compose restart backend")
print("="*60)
