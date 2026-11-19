"""
FACEGUARD AI - Dashboard Blueprint
Module: faceguard/blueprints/dashboard/__init__.py
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from faceguard.extensions import db
from faceguard.models.scan import Scan
from faceguard.utils.security import log_audit

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))
    return redirect(url_for("auth.login"))

@dashboard_bp.route("/login")
def direct_login():
    return redirect(url_for("auth.login"))

@dashboard_bp.route("/register")
def direct_register():
    return redirect(url_for("auth.register"))

@dashboard_bp.route("/overview")
@login_required
def overview():
    """Renders main FaceGuard AI security overview dashboard"""
    total_scans = current_user.scans.count()
    real_scans = current_user.scans.filter_by(overall_prediction="REAL").count()
    fake_scans = current_user.scans.filter_by(overall_prediction="FAKE").count()
    
    avg_conf_query = db.session.query(db.func.avg(Scan.overall_confidence)).filter(
        Scan.user_id == current_user.id,
        Scan.overall_confidence.isnot(None)
    ).scalar()
    avg_confidence = round(float(avg_conf_query or 0.0), 1)

    recent_scans = current_user.scans.order_by(Scan.created_at.desc()).limit(8).all()

    return render_template(
        "dashboard/overview.html",
        total_scans=total_scans,
        real_scans=real_scans,
        fake_scans=fake_scans,
        avg_confidence=avg_confidence,
        recent_scans=recent_scans,
        active_page="overview"
    )

@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User Settings & Preferences"""
    if request.method == "POST":
        theme = request.form.get("theme", "dark")
        sensitivity = request.form.get("sensitivity", "standard")
        email_alerts = bool(request.form.get("email_alerts"))
        
        log_audit("settings_updated", f"Theme: {theme}, Sensitivity: {sensitivity}, Alerts: {email_alerts}")
        flash("Your preferences have been successfully updated.", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template(
        "dashboard/settings.html",
        active_page="settings"
    )
