"""
Email service for sending notifications to users
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', 'gonbik7@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')  # App password
FROM_EMAIL = os.getenv('FROM_EMAIL', 'gonbik7@gmail.com')
FROM_NAME = os.getenv('FROM_NAME', 'LabOS AI Team')

# Frontend URL for links
FRONTEND_URL = os.getenv('AUTH0_BASE_URL', 'https://stella-agent.com')


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None
) -> bool:
    """
    Send an email using Gmail SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        plain_content: Plain text email body (optional, will strip HTML if not provided)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if SMTP is configured
        if not SMTP_PASSWORD:
            logger.warning("⚠️ SMTP_PASSWORD not configured, skipping email send")
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
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent successfully to {to_email}")
        return True
        
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
    
    subject = "🎉 Welcome to LabOS AI - Your Access Has Been Approved!"
    
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
            <h1>🎉 Welcome to LabOS AI!</h1>
        </div>
        <div class="content">
            <p>Hi {display_name} 👋,</p>
            
            <p>Great news! Your application to join LabOS AI has been <strong>approved</strong>! 🚀</p>
            
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
            <strong>The LabOS AI Team</strong></p>
        </div>
        <div class="footer">
            <p>LabOS - Self-Evolving Intelligent Laboratory Assistant</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Hi {display_name} 👋,

    Great news! Your application to join LabOS AI has been approved! 🚀

    You now have full access to our AI-powered biomedical research platform.

    Get started: {FRONTEND_URL}

    If you have any questions or need assistance, feel free to reach out to us.

    Happy researching!

    Best regards,
    The LabOS AI Team

    ---
    LabOS - Self-Evolving Intelligent Laboratory Assistant
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
    
    subject = "🔔 New User Waitlist Application - LabOS AI"
    
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
            <p>A new user has applied to join LabOS AI:</p>
            
            <div class="user-info">
                <strong>Name:</strong> {display_name}<br>
                <strong>Email:</strong> {user_email}
            </div>
            
            <p>Please review their application and approve or reject as appropriate.</p>
            
            <div style="text-align: center;">
                <a href="{FRONTEND_URL}/admin/waitlist" class="button">Review Application →</a>
            </div>
            
            <p style="font-size: 12px; color: #666; margin-top: 30px;">
                This is an automated notification from LabOS AI.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    New Waitlist Application - LabOS AI

    A new user has applied to join LabOS AI:

    Name: {display_name}
    Email: {user_email}

    Please review their application: {FRONTEND_URL}/admin/waitlist

    ---
    This is an automated notification from LabOS AI.
    """
    
    return send_email(admin_email, subject, html_content, plain_content)
