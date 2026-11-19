"""
FACEGUARD AI - Forensic PDF Reports Controller
Module: faceguard/blueprints/reports/__init__.py
"""
import os
from flask import Blueprint, render_template, abort, send_file, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from faceguard.config import Config, BASE_DIR
from faceguard.models.scan import Scan
from faceguard.models.audit import PDFReport
from faceguard.utils.pdf import generate_scan_pdf
from faceguard.utils.security import log_audit

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/")
@login_required
def list_reports():
    """List all generated PDF forensic reports for the current user"""
    reports = PDFReport.query.filter_by(user_id=current_user.id).order_by(PDFReport.created_at.desc()).all()
    
    total_reports = len(reports)
    real_count = sum(1 for r in reports if r.scan and r.scan.overall_prediction == "REAL")
    fake_count = sum(1 for r in reports if r.scan and r.scan.overall_prediction == "FAKE")

    return render_template(
        "reports/list.html",
        active_page="reports",
        reports=reports,
        total_reports=total_reports,
        real_count=real_count,
        fake_count=fake_count
    )

@reports_bp.route("/generate/<scan_uuid>")
@login_required
def generate_report(scan_uuid):
    """Generate or retrieve a PDF forensic report for a user-owned scan"""
    scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first_or_404()

    try:
        pdf_record = generate_scan_pdf(scan)
        log_audit("report_generated", f"Generated PDF for Scan #{scan.scan_uuid[:8]}")
        flash(f"Forensic PDF Dossier #{pdf_record.report_uuid[:8]} compiled successfully.", "success")
        return redirect(url_for("reports.download_report", report_uuid=pdf_record.report_uuid))
    except Exception as e:
        current_app.logger.error(f"PDF generation failed: {str(e)}")
        flash(f"PDF generation failed: {str(e)}", "error")
        return redirect(url_for("history.view_scan", scan_uuid=scan.scan_uuid))

@reports_bp.route("/<report_uuid>")
@reports_bp.route("/<report_uuid>/download")
@login_required
def download_report(report_uuid):
    """Securely download a user-owned PDF forensic report"""
    report = PDFReport.query.filter_by(report_uuid=report_uuid, user_id=current_user.id).first_or_404()

    cleaned_rel = report.file_path.replace("static/", "").replace("static\\", "")
    abs_path = os.path.join(BASE_DIR, "static", cleaned_rel)

    # If missing from disk, re-compile automatically
    if not os.path.exists(abs_path) and report.scan:
        generate_scan_pdf(report.scan, output_path=abs_path)

    if not os.path.exists(abs_path):
        abort(404)

    download_name = f"FaceGuard_Dossier_{report.report_uuid[:8]}.pdf"
    return send_file(
        abs_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf"
    )
