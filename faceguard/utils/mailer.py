"""
FACEGUARD AI - Secure SMTP Mailer Utility
Module: faceguard/utils/mailer.py
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def is_smtp_configured():
    """Checks whether SMTP email credentials have been provided in environment"""
    username = current_app.config.get("MAIL_USERNAME", "")
    password = current_app.config.get("MAIL_PASSWORD", "")
    return bool(username and password and username.lower() != "none" and password.lower() != "none")

def send_email(to_email, subject, html_content):
    """
    Delivers an HTML email using standard SMTP (TLS on port 587 or SSL on port 465)
    Returns (success: bool, message: str)
    """
    if not is_smtp_configured():
        return False, "SMTP credentials not configured. Using local verification fallback."

    server_host = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
    server_port = int(current_app.config.get("MAIL_PORT", 587))
    use_tls = current_app.config.get("MAIL_USE_TLS", True)
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    sender_name = current_app.config.get("MAIL_SENDER_NAME", "FACEGUARD AI Security")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{username}>"
        msg["To"] = to_email

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        if server_port == 465:
            server = smtplib.SMTP_SSL(server_host, server_port, timeout=12)
        else:
            server = smtplib.SMTP(server_host, server_port, timeout=12)
            if use_tls:
                server.starttls()

        server.login(username, password)
        server.sendmail(username, to_email, msg.as_string())
        server.quit()
        return True, "Email successfully delivered."

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication failed. Please check your App Password."
    except Exception as e:
        return False, f"Failed to deliver email: {str(e)}"

def send_otp_email(to_email, otp_code, user_name="User"):
    """Sends a 6-digit email verification code"""
    subject = f"{otp_code} is your FACEGUARD AI Verification Code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; margin: 0; padding: 24px; color: #f1f5f9; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #131b2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 36px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            .brand {{ font-size: 20px; font-weight: 800; color: #38bdf8; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
            .title {{ font-size: 22px; font-weight: 700; color: #ffffff; margin-bottom: 12px; }}
            .text {{ font-size: 15px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: rgba(56, 189, 248, 0.08); border: 1px dashed #38bdf8; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; font-family: monospace; }}
            .footer {{ font-size: 13px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 20px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">FACEGUARD AI</div>
            <div class="title">Verify Your Email Address</div>
            <div class="text">Hello <strong>{user_name}</strong>,<br><br>Thank you for registering on FACEGUARD AI. Please enter the following 6-digit verification code to activate your account:</div>
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
            </div>
            <div class="text" style="font-size: 14px; color: #64748b;">This code expires in <strong>5 minutes</strong>. If you did not create this account, you can safely ignore this email.</div>
            <div class="footer">&copy; 2026 FACEGUARD AI &bull; Autonomous Deepfake Defense System</div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_content)

def send_reset_password_email(to_email, reset_code, user_name="User"):
    """Sends a 6-digit password reset verification code"""
    subject = f"{reset_code} is your FACEGUARD AI Password Reset Code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; margin: 0; padding: 24px; color: #f1f5f9; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #131b2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 36px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            .brand {{ font-size: 20px; font-weight: 800; color: #ef4444; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
            .title {{ font-size: 22px; font-weight: 700; color: #ffffff; margin-bottom: 12px; }}
            .text {{ font-size: 15px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
            .otp-box {{ background: rgba(239, 68, 68, 0.08); border: 1px dashed #ef4444; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px; }}
            .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #ef4444; font-family: monospace; }}
            .footer {{ font-size: 13px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 20px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">FACEGUARD AI</div>
            <div class="title">Password Reset Request</div>
            <div class="text">Hello <strong>{user_name}</strong>,<br><br>We received a request to reset your password. Use the verification code below to proceed:</div>
            <div class="otp-box">
                <div class="otp-code">{reset_code}</div>
            </div>
            <div class="text" style="font-size: 14px; color: #64748b;">This code expires in <strong>5 minutes</strong>. If you did not make this request, secure your account immediately.</div>
            <div class="footer">&copy; 2026 FACEGUARD AI &bull; Autonomous Deepfake Defense System</div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_content)
