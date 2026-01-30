"""
Email service for sending notifications to users
"""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail OAuth2 configuration
GMAIL_USER = os.getenv('GMAIL_USER', 'labos.agent2026@gmail.com')
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID', '')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET', '')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN', '')
GMAIL_ACCESS_TOKEN = os.getenv('GMAIL_ACCESS_TOKEN', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', GMAIL_USER)
FROM_NAME = os.getenv('FROM_NAME', 'LABOS AI Team')

# Frontend URL for links (from env, no hardcoded default)
FRONTEND_URL = os.getenv('FRONTEND_URL') or os.getenv('AUTH0_BASE_URL', 'http://localhost:3000')

# Global Gmail API service instance
_gmail_service = None


def get_gmail_service():
    """
    Get or create Gmail API service instance with OAuth2 credentials

    Returns:
        Gmail API service instance
    """
    global _gmail_service

    if _gmail_service is not None:
        return _gmail_service

    try:
        # Check if OAuth2 credentials are configured
        if not GMAIL_REFRESH_TOKEN:
            logger.warning("⚠️ GMAIL_REFRESH_TOKEN not configured, email service unavailable")
            return None

        # Create credentials from refresh token
        creds = Credentials(
            token=GMAIL_ACCESS_TOKEN,
            refresh_token=GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GMAIL_CLIENT_ID,
            client_secret=GMAIL_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )

        # Refresh the token if needed
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing Gmail OAuth2 access token...")
                creds.refresh(Request())
                logger.info("✅ Gmail OAuth2 token refreshed successfully")

        # Build Gmail API service
        _gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("✅ Gmail API service initialized successfully")
        return _gmail_service

    except Exception as e:
        logger.error(f"❌ Failed to initialize Gmail API service: {e}")
        return None


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None
) -> bool:
    """
    Send an email using Gmail API with OAuth2

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        plain_content: Plain text email body (optional, will strip HTML if not provided)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get Gmail service
        service = get_gmail_service()
        if service is None:
            logger.warning("⚠️ Gmail service not available, skipping email send")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'{FROM_NAME} <{FROM_EMAIL}>'
        msg['To'] = to_email

        # Add plain text version
        if plain_content:
            part1 = MIMEText(plain_content, 'plain')
            msg.attach(part1)

        # Add HTML version
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)

        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        message_body = {'raw': raw_message}

        # Send email via Gmail API
        service.users().messages().send(userId='me', body=message_body).execute()

        logger.info(f"✅ Email sent successfully to {to_email}")
        return True

    except HttpError as e:
        logger.error(f"❌ Gmail API error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}")
        return False


def send_approval_email(user_email: str, user_name: Optional[str] = None) -> bool:
    """
    Send approval notification email to user
    
    Args:
        user_email: User's email address
        user_name: User's name (optional)
    
    Returns:
        bool: True if email sent successfully
    """
    # Use user's actual name if provided, otherwise use first part of email
    if user_name and user_name.strip():
        display_name = user_name.strip()
    else:
        display_name = user_email.split('@')[0]
    
    subject = "🎉 Welcome to LABOS - Your Access Has Been Approved!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: #0ea5e9;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Welcome to LABOS!</h1>
        </div>
        <div class="content">
            <p>Hi {display_name} 👋,</p>
            
            <p>Great news! Your application to join LABOS AI has been <strong>approved</strong>! 🚀</p>
            
            <p>You now have full access to our AI-powered biomedical research platform. Here's what you can do:</p>
            
            <ul>
                <li>💬 Chat with our AI assistant for research support</li>
                <li>🔬 Run automated bioinformatics workflows</li>
                <li>📊 Analyze and visualize your data</li>
                <li>📚 Search and analyze scientific literature</li>
                <li>🧬 Access powerful genomics tools</li>
            </ul>
            
            <div style="text-align: center;">
                <a href="{FRONTEND_URL}" class="button">Get Started Now →</a>
            </div>
            
            <p>If you have any questions or need assistance, feel free to reach out to us at any time.</p>
            
            <p>Happy researching! 🔬✨</p>
            
            <p>Best regards,<br>
            <strong>The LABOS AI Team</strong></p>
        </div>
        <div class="footer">
            <p>LABOS - Self-Evolving Intelligent Laboratory Assistant</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Hi {display_name} 👋,

    Great news! Your application to join LABOS AI has been approved! 🚀

    You now have full access to our AI-powered biomedical research platform.

    Get started: {FRONTEND_URL}

    If you have any questions or need assistance, feel free to reach out to us.

    Happy researching!

    Best regards,
    The LABOS AI Team

    ---
    LABOS - Self-Evolving Intelligent Laboratory Assistant
    This is an automated message. Please do not reply to this email.
    """
    
    return send_email(user_email, subject, html_content, plain_content)


def send_admin_notification(admin_email: str, user_email: str, user_name: Optional[str] = None) -> bool:
    """
    Send notification to admin when a new user joins waitlist
    
    Args:
        admin_email: Admin's email address
        user_email: New user's email
        user_name: New user's name (optional)
    
    Returns:
        bool: True if email sent successfully
    """
    # Use actual name if provided, otherwise indicate it's a new user
    if user_name and user_name.strip():
        display_name = user_name.strip()
    else:
        display_name = "A new user"
    
    subject = "🔔 New User Waitlist Application - LABOS AI"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: #334155;
                color: white;
                padding: 20px;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .user-info {{
                background: white;
                padding: 15px;
                border-left: 4px solid #0ea5e9;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background: #0ea5e9;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 0;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🔔 New Waitlist Application</h2>
        </div>
        <div class="content">
            <p>A new user has applied to join LABOS AI:</p>
            
            <div class="user-info">
                <strong>Name:</strong> {display_name}<br>
                <strong>Email:</strong> {user_email}
            </div>
            
            <p>Please review their application and approve or reject as appropriate.</p>
            
            <div style="text-align: center;">
                <a href="{FRONTEND_URL}/admin/waitlist" class="button">Review Application →</a>
            </div>
            
            <p style="font-size: 12px; color: #666; margin-top: 30px;">
                This is an automated notification from LABOS AI.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    New Waitlist Application - LABOS AI

    A new user has applied to join LABOS AI:

    Name: {display_name}
    Email: {user_email}

    Please review their application: {FRONTEND_URL}/admin/waitlist

    ---
    This is an automated notification from LABOS AI.
    """
    
    return send_email(admin_email, subject, html_content, plain_content)
