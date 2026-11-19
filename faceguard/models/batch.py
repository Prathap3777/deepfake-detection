"""
FACEGUARD AI - Batch Processing Models
Module: faceguard/models/batch.py
"""
import uuid
from datetime import datetime, timezone
from faceguard.extensions import db

def get_utc_now():
    return datetime.now(timezone.utc)

class BatchJob(db.Model):
    __tablename__ = "batch_jobs"

    id = db.Column(db.Integer, primary_key=True)
    batch_uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    title = db.Column(db.String(120), default="Batch Investigation")
    total_files = db.Column(db.Integer, default=0, nullable=False)
    processed_files = db.Column(db.Integer, default=0, nullable=False)
    real_count = db.Column(db.Integer, default=0, nullable=False)
    fake_count = db.Column(db.Integer, default=0, nullable=False)
    failed_count = db.Column(db.Integer, default=0, nullable=False)

    threat_rate = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="completed", nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    items = db.relationship("BatchItem", backref="batch", lazy="select", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BatchJob {self.batch_uuid[:8]} ({self.processed_files}/{self.total_files})>"

class BatchItem(db.Model):
    __tablename__ = "batch_items"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch_jobs.id"), nullable=False, index=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=True, index=True)

    original_filename = db.Column(db.String(255), nullable=False)
    saved_filename = db.Column(db.String(255), nullable=False)
    face_count = db.Column(db.Integer, default=0, nullable=False)
    prediction = db.Column(db.String(10), nullable=True)  # 'REAL', 'FAKE', 'NO_FACE'
    confidence = db.Column(db.Float, default=0.0)
    risk_score = db.Column(db.Float, default=0.0)
    review_priority = db.Column(db.String(40), default="Lower Review Priority")
    status = db.Column(db.String(20), default="completed", nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    thumbnail_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<BatchItem {self.original_filename} ({self.prediction})>"
