"""
Module: mailer.py
Purpose: Secure SMTP Email Delivery for OTP Verification & Password Reset
Supports Gmail, Outlook, or any standard SMTP service via Environment Variables
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SMTP Configuration
SMTP_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("MAIL_PORT", 587))
SMTP_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
SMTP_USERNAME = os.environ.get("MAIL_USERNAME", "")
SMTP_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
SENDER_NAME = os.environ.get("MAIL_SENDER_NAME", "Deepfake Face Authenticity AI")

def is_smtp_configured():
    """Checks whether email credentials have been configured in environment"""
    return bool(SMTP_USERNAME and SMTP_PASSWORD)

def send_email(to_email, subject, html_content):
    """
    Delivers an HTML email using SMTP
    Returns (success: bool, message: str)
    """
    if not is_smtp_configured():
        return False, "SMTP email credentials not configured in .env file. Please configure MAIL_USERNAME and MAIL_PASSWORD."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SMTP_USERNAME}>"
        msg["To"] = to_email

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        # Connect to SMTP server
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=12)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=12)
            if SMTP_USE_TLS:
                server.starttls()

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        server.quit()
        return True, "Verification email sent successfully."

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication failed. Please check your email and App Password."
    except Exception as e:
        return False, f"Failed to deliver email: {str(e)}"

def send_otp_email(to_email, otp_code, user_name="User"):
    """
    Sends a formatted 6-digit OTP verification email
    """
    subject = f"{otp_code} is your FaceAuthentic verification code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .brand {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
            .title {{ font-size: 22px; font-weight: 700; color: #111827; margin-bottom: 12px; }}
            .text {{ font-size: 15px; color: #4b5563; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #0f172a; font-family: monospace; }}
            .footer {{ font-size: 13px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 16px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="brand">Deepfake Image Detection AI</div>
            <div class="title">Verify your email address</div>
            <div class="text">Hello <strong>{user_name}</strong>,<br><br>Thank you for signing up. Please enter the following 6-digit verification code to activate your account:</div>
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
            </div>
            <div class="text" style="font-size: 14px; color: #6b7280;">This code will expire in <strong>5 minutes</strong>. If you did not create an account, you can safely ignore this email.</div>
            <div class="footer">&copy; 2026 Deepfake Face Authenticity AI &bull; Automated Security Service</div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_content)

def send_reset_password_email(to_email, reset_code, user_name="User"):
    """
    Sends a formatted password reset verification code
    """
    subject = f"{reset_code} is your Password Reset Code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .brand {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 24px; }}
            .title {{ font-size: 22px; font-weight: 700; color: #111827; margin-bottom: 12px; }}
            .text {{ font-size: 15px; color: #4b5563; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: #fef2f2; border: 1px dashed #fecaca; border-radius: 8px; padding: 18px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #dc2626; font-family: monospace; }}
            .footer {{ font-size: 13px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 16px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="brand">Deepfake Image Detection AI</div>
            <div class="title">Password Reset Request</div>
            <div class="text">Hello <strong>{user_name}</strong>,<br><br>We received a request to reset your password. Use the following verification code to proceed:</div>
            <div class="otp-box">
                <div class="otp-code">{reset_code}</div>
            </div>
            <div class="text" style="font-size: 14px; color: #6b7280;">This code will expire in <strong>5 minutes</strong>. If you did not request a password reset, please secure your account immediately.</div>
            <div class="footer">&copy; 2026 Deepfake Face Authenticity AI &bull; Automated Security Service</div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_content)
