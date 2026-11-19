"""
FACEGUARD AI - Forensic Chat Assistant Models
Module: faceguard/models/chat.py
"""
import uuid
from datetime import datetime, timezone
from faceguard.extensions import db

def get_utc_now():
    return datetime.now(timezone.utc)

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=True, index=True)
    title = db.Column(db.String(120), default="Forensic Investigation Session")
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    messages = db.relationship("ChatMessage", backref="session", lazy="select", cascade="all, delete-orphan", order_by="ChatMessage.created_at.asc()")
    scan = db.relationship("Scan", backref=db.backref("chat_sessions", lazy="select"))

    def __repr__(self):
        return f"<ChatSession {self.session_uuid[:8]} (User {self.user_id})>"

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = db.Column(db.Text, nullable=False)
    source_attribution = db.Column(db.String(50), default="forensic_engine")  # 'forensic_engine' or 'llm_api'
    created_at = db.Column(db.DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<ChatMessage {self.id} from {self.sender}>"
