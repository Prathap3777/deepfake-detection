"""
FACEGUARD AI - Security & Audit Helper Utilities
Module: faceguard/utils/security.py
"""
from functools import wraps
from flask import request, abort, current_app
from flask_login import current_user, login_required
from faceguard.extensions import db
from faceguard.models.audit import AuditLog

def log_audit(action, details=None, user_id=None):
    """Logs security audit actions with IP address and user-agent"""
    try:
        uid = user_id or (current_user.id if current_user.is_authenticated else None)
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        ua = request.headers.get("User-Agent", "")[:250]

        entry = AuditLog(
            user_id=uid,
            action=action,
            ip_address=ip,
            user_agent=ua,
            details=details
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to record audit log: {str(e)}")

def admin_required(f):
    """Restricts access strictly to authenticated administrators"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            log_audit("unauthorized_admin_access_attempt", f"Attempted path: {request.path}")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
