"""
FACEGUARD AI - Audit, Report & Feedback Models
Module: faceguard/models/audit.py
"""
import uuid
from datetime import datetime, timezone
from faceguard.extensions import db

def get_utc_now():
    return datetime.now(timezone.utc)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} at {self.timestamp}>"

class PDFReport(db.Model):
    __tablename__ = "pdf_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    file_path = db.Column(db.String(255), nullable=False)
    file_size_bytes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)

    def __repr__(self):
        return f"<PDFReport {self.report_uuid[:8]} for Scan {self.scan_id}>"

class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    rating = db.Column(db.Integer, default=5, nullable=False)
    category = db.Column(db.String(50), default="General")
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)
