"""
FACEGUARD AI - Detection History Controller
Module: faceguard/blueprints/history/__init__.py
"""
import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from faceguard.config import Config
from faceguard.extensions import db
from faceguard.models.scan import Scan, FaceResult, VideoFrame
from faceguard.utils.security import log_audit

history_bp = Blueprint("history", __name__)

@history_bp.route("/")
@login_required
def list_history():
    """
    Paginated, searchable, and filterable audit history of user-owned scans.
    Strictly isolated: users can only view their own records.
    """
    q = request.args.get("q", "").strip()
    media_type = request.args.get("media_type", "all").strip().lower()
    verdict = request.args.get("verdict", "all").strip().upper()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Scan.query.filter_by(user_id=current_user.id)

    # 1. Search Query (Filename or UUID)
    if q:
        query = query.filter(
            db.or_(
                Scan.original_filename.ilike(f"%{q}%"),
                Scan.scan_uuid.ilike(f"%{q}%"),
                Scan.sha256.ilike(f"%{q}%")
            )
        )

    # 2. Filter by Media Type (image / video)
    if media_type in ("image", "video"):
        query = query.filter_by(media_type=media_type)

    # 3. Filter by Prediction Verdict (REAL / FAKE)
    if verdict in ("REAL", "FAKE"):
        query = query.filter_by(overall_prediction=verdict)

    # 4. Filter by Date Range
    if date_from:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Scan.created_at >= d_from)
        except ValueError:
            pass

    if date_to:
        try:
            # End of day
            d_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Scan.created_at <= d_to)
        except ValueError:
            pass

    # Order newest first
    query = query.order_by(Scan.created_at.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "history/list.html",
        active_page="history",
        scans=pagination.items,
        pagination=pagination,
        q=q,
        media_type=media_type,
        verdict=verdict,
        date_from=date_from,
        date_to=date_to,
        total_count=pagination.total
    )

@history_bp.route("/<scan_uuid>")
@login_required
def view_scan(scan_uuid):
    """Detailed forensic inspection view for a single user-owned scan"""
    scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first_or_404()
    return render_template(
        "history/detail.html",
        active_page="history",
        scan=scan
    )

@history_bp.route("/<scan_uuid>/delete", methods=["POST"])
@login_required
def delete_scan(scan_uuid):
    """Deletes a user-owned scan and its file artifacts on disk"""
    scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first_or_404()

    # Safely remove uploaded media file
    if scan.saved_filename:
        upload_path = os.path.join(Config.UPLOAD_FOLDER, scan.saved_filename)
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except OSError:
                pass

    # Remove database record (Cascade will delete child FaceResults and VideoFrames)
    db.session.delete(scan)
    db.session.commit()

    log_audit("scan_deleted", f"Deleted scan record #{scan_uuid[:8]} ({scan.original_filename})")
    flash(f"Scan #{scan_uuid[:8]} has been deleted successfully.", "success")
    return redirect(url_for("history.list_history"))
