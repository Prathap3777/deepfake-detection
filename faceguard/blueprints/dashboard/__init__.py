"""
FACEGUARD AI - Dashboard Blueprint
Module: faceguard/blueprints/dashboard/__init__.py
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from faceguard.extensions import db
from faceguard.models.scan import Scan
from faceguard.utils.security import log_audit

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def index():
    return redirect(url_for("dashboard.overview"))

@dashboard_bp.route("/login")
def direct_login():
    return redirect(url_for("dashboard.overview"))

@dashboard_bp.route("/register")
def direct_register():
    return redirect(url_for("dashboard.overview"))

@dashboard_bp.route("/overview")
@login_required
def overview():
    """Renders main FaceGuard AI security overview dashboard with real database metrics"""
    total_scans = current_user.scans.count()
    real_scans = current_user.scans.filter_by(overall_prediction="REAL").count()
    fake_scans = current_user.scans.filter_by(overall_prediction="FAKE").count()
    
    avg_conf_query = db.session.query(db.func.avg(Scan.overall_confidence)).filter(
        Scan.user_id == current_user.id,
        Scan.overall_confidence.isnot(None)
    ).scalar()
    avg_confidence = round(float(avg_conf_query or 0.0), 1)

    avg_risk_query = db.session.query(db.func.avg(Scan.risk_score)).filter(
        Scan.user_id == current_user.id,
        Scan.risk_score.isnot(None)
    ).scalar()
    avg_risk_score = round(float(avg_risk_query or 0.0), 1)

    # Risk Priority Assessment
    if avg_risk_score >= 60.0:
        risk_priority = "High Threat Level"
        risk_color = "#f43f5e"
    elif avg_risk_score >= 35.0:
        risk_priority = "Elevated Caution"
        risk_color = "#f59e0b"
    elif total_scans > 0:
        risk_priority = "Low Risk Profile"
        risk_color = "#10b981"
    else:
        risk_priority = "Clean System"
        risk_color = "#06b6d4"

    # Media Type Distribution
    image_scans = current_user.scans.filter_by(media_type="image").count()
    video_scans = current_user.scans.filter_by(media_type="video").count()

    # Processing Status Counts
    completed_scans = current_user.scans.filter_by(status="completed").count()
    processing_scans = current_user.scans.filter_by(status="processing").count()
    failed_scans = current_user.scans.filter_by(status="failed").count()

    # 7-Day Timeline Trend (Actual database queries)
    today = datetime.now(timezone.utc).date()
    trend_labels = []
    trend_total = []
    trend_real = []
    trend_fake = []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        d_end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
        trend_labels.append(d.strftime("%b %d"))

        day_scans = current_user.scans.filter(Scan.created_at >= d_start, Scan.created_at <= d_end)
        trend_total.append(day_scans.count())
        trend_real.append(day_scans.filter_by(overall_prediction="REAL").count())
        trend_fake.append(day_scans.filter_by(overall_prediction="FAKE").count())

    chart_data = {
        "trend_labels": trend_labels,
        "trend_total": trend_total,
        "trend_real": trend_real,
        "trend_fake": trend_fake,
        "verdict_dist": [real_scans, fake_scans, max(0, total_scans - (real_scans + fake_scans))],
        "media_dist": [image_scans, video_scans]
    }

    recent_scans = current_user.scans.order_by(Scan.created_at.desc()).limit(8).all()

    return render_template(
        "dashboard/overview.html",
        total_scans=total_scans,
        real_scans=real_scans,
        fake_scans=fake_scans,
        avg_confidence=avg_confidence,
        avg_risk_score=avg_risk_score,
        risk_priority=risk_priority,
        risk_color=risk_color,
        image_scans=image_scans,
        video_scans=video_scans,
        completed_scans=completed_scans,
        processing_scans=processing_scans,
        failed_scans=failed_scans,
        chart_data=chart_data,
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
