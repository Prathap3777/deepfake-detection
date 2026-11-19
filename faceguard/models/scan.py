"""
FACEGUARD AI - Scan & Analysis Models
Module: faceguard/models/scan.py
"""
import uuid
from datetime import datetime, timezone
from faceguard.extensions import db

def get_utc_now():
    return datetime.now(timezone.utc)

class Scan(db.Model):
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    scan_uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    media_type = db.Column(db.String(10), default="image", nullable=False)  # 'image' or 'video'
    original_filename = db.Column(db.String(255), nullable=False)
    saved_filename = db.Column(db.String(255), nullable=False)
    sha256 = db.Column(db.String(64), nullable=True, index=True)

    face_count = db.Column(db.Integer, default=0, nullable=False)
    overall_prediction = db.Column(db.String(10), nullable=True)  # 'REAL' or 'FAKE'
    overall_confidence = db.Column(db.Float, default=0.0)
    real_probability = db.Column(db.Float, default=0.0)
    fake_probability = db.Column(db.Float, default=0.0)

    # Annotated result image / video thumbnail path
    annotated_path = db.Column(db.String(255), nullable=True)
    analysis_mode = db.Column(db.String(20), default="standard")  # 'standard' or 'portrait'
    analysis_status = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="completed", nullable=False)  # 'processing', 'completed', 'failed'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    # Relationships
    faces = db.relationship("FaceResult", backref="scan", lazy="select", cascade="all, delete-orphan")
    video_frames = db.relationship("VideoFrame", backref="scan", lazy="select", cascade="all, delete-orphan")
    reports = db.relationship("PDFReport", backref="scan", lazy="select", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan {self.scan_uuid[:8]} ({self.media_type}: {self.overall_prediction})>"

class FaceResult(db.Model):
    __tablename__ = "face_results"

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=False, index=True)
    face_index = db.Column(db.Integer, default=1, nullable=False)

    # Bounding Box Coordinates (x, y, w, h)
    bbox_x = db.Column(db.Integer, nullable=True)
    bbox_y = db.Column(db.Integer, nullable=True)
    bbox_w = db.Column(db.Integer, nullable=True)
    bbox_h = db.Column(db.Integer, nullable=True)

    prediction = db.Column(db.String(10), nullable=False)  # 'REAL' or 'FAKE'
    confidence = db.Column(db.Float, default=0.0, nullable=False)
    real_probability = db.Column(db.Float, default=0.0)
    fake_probability = db.Column(db.Float, default=0.0)

    # Artifact image relative paths
    face_crop_path = db.Column(db.String(255), nullable=True)
    gradcam_path = db.Column(db.String(255), nullable=True)
    ela_path = db.Column(db.String(255), nullable=True)
    fft_path = db.Column(db.String(255), nullable=True)

    # Forensic signal values
    sensor_variance = db.Column(db.Float, nullable=True)
    fft_ratio = db.Column(db.Float, nullable=True)
    ela_mean = db.Column(db.Float, nullable=True)
    chroma_score = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)

class VideoFrame(db.Model):
    __tablename__ = "video_frames"

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=False, index=True)

    frame_index = db.Column(db.Integer, nullable=False)
    timestamp_sec = db.Column(db.Float, nullable=False)
    frame_path = db.Column(db.String(255), nullable=False)

    face_detected = db.Column(db.Boolean, default=False, nullable=False)
    prediction = db.Column(db.String(10), nullable=True)
    confidence = db.Column(db.Float, default=0.0)
    is_suspicious = db.Column(db.Boolean, default=False)
