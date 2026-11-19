"""
FACEGUARD AI - User & Authentication Models
Module: faceguard/models/user.py
"""
import random
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from faceguard.extensions import db, login_manager

def get_utc_now():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)  # 'user' or 'admin'
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    # 6-digit OTP verification
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime(timezone=True), nullable=True)
    otp_attempts = db.Column(db.Integer, default=0, nullable=False)

    # Password reset verification
    reset_token = db.Column(db.String(6), nullable=True)
    reset_expiry = db.Column(db.DateTime(timezone=True), nullable=True)

    # Metadata & timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    scans = db.relationship("Scan", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    reports = db.relationship("PDFReport", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    feedbacks = db.relationship("Feedback", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def generate_otp(self):
        """Generates a secure 6-digit OTP code valid for 5 minutes"""
        self.otp_code = f"{random.randint(100000, 999999)}"
        self.otp_expiry = get_utc_now() + timedelta(minutes=5)
        self.otp_attempts = 0
        return self.otp_code

    def verify_otp(self, input_code):
        """Verifies provided OTP against expiration and maximum attempts"""
        if not self.otp_code or not self.otp_expiry:
            return False, "No active verification code found."

        # Handle timezone compatibility
        now = get_utc_now()
        expiry = self.otp_expiry if self.otp_expiry.tzinfo else self.otp_expiry.replace(tzinfo=timezone.utc)
        if now > expiry:
            return False, "Verification code has expired. Please request a new one."

        if self.otp_attempts >= 5:
            return False, "Maximum verification attempts exceeded. Please request a new code."

        if self.otp_code.strip() != input_code.strip():
            self.otp_attempts += 1
            remaining = max(0, 5 - self.otp_attempts)
            return False, f"Incorrect code. ({remaining} attempts remaining)"

        # Successful verification
        self.is_verified = True
        self.otp_code = None
        self.otp_expiry = None
        self.otp_attempts = 0
        return True, "Email successfully verified."

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
