"""
FACEGUARD AI - Configuration System
Module: faceguard/config.py
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class Config:
    """Base Configuration"""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "faceguard-ai-secret-key-2026-production")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'faceguard.db')}"
    )
    # Handle PostgreSQL prefix compatibility (postgres:// -> postgresql://)
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads & Storage
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    REPORT_FOLDER = os.path.join(BASE_DIR, "static", "reports")
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB maximum upload size (allows small video files)
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}

    # Security & Rate Limiting
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_TIME_LIMIT = 3600

    # Model & Cascade Paths
    MODEL_PATH = os.path.join(BASE_DIR, "model", "deepfake_detector.pt")
    CLASSES_PATH = os.path.join(BASE_DIR, "model", "classes.json")
    CASCADE_PATH = os.path.join(BASE_DIR, "model", "haarcascade_frontalface_default.xml")

    # Mail Configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_SENDER_NAME = os.environ.get("MAIL_SENDER_NAME", "FACEGUARD AI Security")

    # Direct Access / No Login Wall
    AUTO_LOGIN_ENABLED = True

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    TESTING = True
    AUTO_LOGIN_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
