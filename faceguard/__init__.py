"""
FACEGUARD AI - Application Factory Package
Module: faceguard/__init__.py
"""
import os
import sqlite3
from flask import Flask
from faceguard.config import Config, BASE_DIR
from faceguard.extensions import db, login_manager, csrf

def create_app(config_class=Config):
    """
    Application Factory Pattern for FACEGUARD AI
    Creates, configures and returns the Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
    )

    # Load Configuration
    app.config.from_object(config_class)

    # Initialize Flask Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Ensure Upload and Report Storage Folders Exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)

    with app.app_context():
        # Import models so SQLAlchemy registers them
        from faceguard.models import User, Scan, FaceResult, VideoFrame, AuditLog, PDFReport, Feedback, BatchJob, BatchItem, ChatSession, ChatMessage
        db.create_all()

        # Migrate existing users from users.db if present
        migrate_legacy_users(app)

    # Register Blueprint Controllers
    register_blueprints(app)

    # Seamless Direct Access: Auto-authenticate default user session
    @app.before_request
    def auto_authenticate_user():
        if app.config.get("AUTO_LOGIN_ENABLED", True) and not app.config.get("TESTING", False):
            from flask_login import current_user, login_user
            if not current_user.is_authenticated:
                from faceguard.models.user import User
                user = User.query.filter_by(email="prathapprathap8953@gmail.com").first()
                if not user:
                    user = User.query.first()
                if not user:
                    user = User(
                        full_name="Prathap",
                        email="prathapprathap8953@gmail.com",
                        role="admin",
                        is_verified=True
                    )
                    user.set_password("faceguard2026")
                    db.session.add(user)
                    db.session.commit()
                else:
                    if not user.is_verified:
                        user.is_verified = True
                        db.session.commit()
                login_user(user, remember=True)

    # Security Hardening HTTP Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app

def register_blueprints(app):
    """Registers modular Flask Blueprints"""
    from faceguard.blueprints.auth import auth_bp
    from faceguard.blueprints.dashboard import dashboard_bp
    from faceguard.blueprints.detect import detect_bp
    from faceguard.blueprints.history import history_bp
    from faceguard.blueprints.analytics import analytics_bp
    from faceguard.blueprints.reports import reports_bp
    from faceguard.blueprints.admin import admin_bp
    from faceguard.blueprints.chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(detect_bp, url_prefix="/detect")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(history_bp, url_prefix="/history")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")

def migrate_legacy_users(app):
    """
    Safety Migration Utility:
    Transfers accounts from legacy users.db to new SQLAlchemy schema
    """
    legacy_db = os.path.join(BASE_DIR, "users.db")
    if not os.path.exists(legacy_db):
        return

    from faceguard.models.user import User

    try:
        conn = sqlite3.connect(legacy_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            conn.close()
            return

        rows = cursor.execute("SELECT * FROM users").fetchall()
        migrated_count = 0

        for r in rows:
            email = r["email"].strip().lower()
            existing = User.query.filter_by(email=email).first()
            if not existing:
                new_user = User(
                    full_name=r["full_name"],
                    email=email,
                    password_hash=r["password_hash"],
                    is_verified=bool(r["is_verified"]),
                    role="admin" if "admin" in email else "user"
                )
                db.session.add(new_user)
                migrated_count += 1

        if migrated_count > 0:
            db.session.commit()
            app.logger.info(f"[✓] Migrated {migrated_count} legacy user(s) to FACEGUARD AI database.")

        conn.close()
    except Exception as e:
        app.logger.warning(f"Legacy migration skipped or error: {str(e)}")
