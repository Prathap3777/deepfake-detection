"""
FACEGUARD AI - Administration Blueprint & Security Control Center
Module: faceguard/blueprints/admin/__init__.py
"""
import platform
try:
    import psutil
except ImportError:
    psutil = None
from datetime import datetime, timezone
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan
from faceguard.models.audit import AuditLog, PDFReport
from faceguard.utils.security import log_audit

admin_bp = Blueprint("admin", __name__)

@admin_bp.before_request
@login_required
def ensure_admin():
    """Enforces strict role-based access control for all admin routes"""
    if not current_user.is_admin():
        log_audit("unauthorized_admin_access_attempt", f"Attempted path: {request.path}")
        abort(403)

@admin_bp.route("/")
def admin_overview():
    """System Administrator Control Panel Overview & Global Threat Telemetry"""
    total_users = User.query.count()
    verified_users = User.query.filter_by(is_verified=True).count()
    admin_users = User.query.filter_by(role="admin").count()
    
    total_scans = Scan.query.count()
    fake_scans = Scan.query.filter_by(overall_prediction="FAKE").count()
    real_scans = Scan.query.filter_by(overall_prediction="REAL").count()
    threat_rate = round((fake_scans / total_scans * 100), 1) if total_scans > 0 else 0.0

    total_audits = AuditLog.query.count()
    total_reports = PDFReport.query.count()

    # Hardware & Runtime Telemetry
    mem_used_mb = 180.0
    mem_percent = 35.0
    if psutil is not None:
        try:
            mem = psutil.virtual_memory()
            mem_used_mb = round(mem.used / (1024 * 1024), 1)
            mem_percent = mem.percent
        except Exception:
            pass

    system_telemetry = {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "runtime_engine": "PyTorch 2.x (CPU Inference Mode - Render 512MB RAM Safe)",
        "memory_used_mb": mem_used_mb,
        "memory_percent": mem_percent,
        "cascade_model": "OpenCV Haar Cascade FrontalFace v4.9",
        "deepfake_model": "DeepfakeDetectorCNN (ResNet-18 Backbone)",
        "explainability_engine": "Grad-CAM Target Layer4[-1]"
    }

    # Recent Scans Across All Tenants
    recent_scans = Scan.query.order_by(Scan.created_at.desc()).limit(8).all()

    # Recent Security Audit Trail
    recent_audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    return render_template(
        "admin/overview.html",
        active_page="admin_overview",
        total_users=total_users,
        verified_users=verified_users,
        admin_users=admin_users,
        total_scans=total_scans,
        fake_scans=fake_scans,
        real_scans=real_scans,
        threat_rate=threat_rate,
        total_audits=total_audits,
        total_reports=total_reports,
        telemetry=system_telemetry,
        recent_scans=recent_scans,
        recent_audits=recent_audits
    )

@admin_bp.route("/audit")
def audit_logs():
    """Security Audit Trail Inspector with Multi-Criteria Filtering"""
    action_filter = request.args.get("action", "").strip()
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if search_query:
        query = query.outerjoin(User).filter(
            db.or_(
                AuditLog.ip_address.ilike(f"%{search_query}%"),
                AuditLog.details.ilike(f"%{search_query}%"),
                AuditLog.action.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%"),
                User.full_name.ilike(f"%{search_query}%")
            )
        )

    pagination = query.paginate(page=page, per_page=20, error_out=False)

    # Distinct actions for filter dropdown
    distinct_actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all() if r[0]]

    return render_template(
        "admin/audit_logs.html",
        active_page="admin_audit",
        pagination=pagination,
        logs=pagination.items,
        distinct_actions=distinct_actions,
        selected_action=action_filter,
        search_query=search_query
    )

@admin_bp.route("/users")
def user_management():
    """User Management, Role Assignments & Access Control Directory"""
    role_filter = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = User.query.order_by(User.created_at.desc())

    if role_filter in ("admin", "user"):
        query = query.filter(User.role == role_filter)

    if status_filter == "verified":
        query = query.filter(User.is_verified == True)
    elif status_filter == "unverified":
        query = query.filter(User.is_verified == False)

    if search_query:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%")
            )
        )

    pagination = query.paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "admin/users.html",
        active_page="admin_users",
        pagination=pagination,
        users=pagination.items,
        selected_role=role_filter,
        selected_status=status_filter,
        search_query=search_query
    )

@admin_bp.route("/users/<int:user_id>/toggle-role", methods=["POST"])
def toggle_user_role(user_id):
    """Promotes or demotes user role between 'user' and 'admin'"""
    if user_id == current_user.id:
        flash("Action rejected: You cannot alter your own administrative role.", "warning")
        return redirect(url_for("admin.user_management"))

    user = db.get_or_404(User, user_id)
    new_role = "user" if user.role == "admin" else "admin"
    user.role = new_role
    db.session.commit()

    log_audit("admin_role_changed", f"Changed role of user {user.email} to '{new_role}'", user_id=current_user.id)
    flash(f"User role updated to '{new_role.upper()}' for {user.full_name} ({user.email}).", "success")
    return redirect(url_for("admin.user_management"))

@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
def toggle_user_status(user_id):
    """Toggles email verification status of an account"""
    user = db.get_or_404(User, user_id)
    user.is_verified = not user.is_verified
    db.session.commit()

    status_label = "Verified" if user.is_verified else "Unverified"
    log_audit("admin_status_changed", f"Updated account status of {user.email} to '{status_label}'", user_id=current_user.id)
    flash(f"Account status for {user.email} marked as {status_label}.", "info")
    return redirect(url_for("admin.user_management"))

@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    """Permanently purges a user account and associated detection records"""
    if user_id == current_user.id:
        flash("Action rejected: You cannot delete your own administrative account.", "danger")
        return redirect(url_for("admin.user_management"))

    user = db.get_or_404(User, user_id)
    target_email = user.email
    db.session.delete(user)
    db.session.commit()

    log_audit("admin_user_deleted", f"Permanently deleted user account {target_email}", user_id=current_user.id)
    flash(f"User account '{target_email}' and all associated scans have been purged.", "info")
    return redirect(url_for("admin.user_management"))
