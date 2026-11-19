"""
FACEGUARD AI - Forensic Chat Assistant Controller
Module: faceguard/blueprints/chat/__init__.py
"""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from faceguard.extensions import db
from faceguard.models.scan import Scan
from faceguard.models.chat import ChatSession, ChatMessage
from faceguard.core.chat import generate_chat_response
from faceguard.utils.security import log_audit

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/")
@login_required
def chat_index():
    """Main Chat Assistant landing page. Loads active session or creates default one."""
    scan_uuid = request.args.get("scan_uuid", "").strip()
    session_uuid = request.args.get("session_uuid", "").strip()

    # Get user's recent scans for the context selector
    user_scans = Scan.query.filter_by(user_id=current_user.id, status="completed")\
                           .order_by(Scan.created_at.desc()).limit(20).all()

    # Get user's recent chat sessions
    user_sessions = ChatSession.query.filter_by(user_id=current_user.id)\
                                     .order_by(ChatSession.updated_at.desc()).limit(15).all()

    active_session = None

    if session_uuid:
        active_session = ChatSession.query.filter_by(session_uuid=session_uuid, user_id=current_user.id).first()

    # If scan_uuid requested, find or create a session attached to that scan
    if not active_session and scan_uuid:
        target_scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first()
        if target_scan:
            active_session = ChatSession.query.filter_by(scan_id=target_scan.id, user_id=current_user.id).first()
            if not active_session:
                active_session = ChatSession(
                    user_id=current_user.id,
                    scan_id=target_scan.id,
                    title=f"Analysis of {target_scan.original_filename[:20]}"
                )
                db.session.add(active_session)
                db.session.commit()
                # Add initial greeting message
                welcome_msg = ChatMessage(
                    session_id=active_session.id,
                    sender="assistant",
                    content=f"Hello! I am your FaceGuard AI Forensic Assistant. I have loaded the investigation context for **`{target_scan.original_filename}`** ({target_scan.overall_prediction}, {target_scan.overall_confidence:.1f}% certainty).\n\nWhat would you like to know about this scan?",
                    source_attribution="forensic_engine"
                )
                db.session.add(welcome_msg)
                db.session.commit()

    # If still no active session, pick most recent or create fresh one
    if not active_session and user_sessions:
        active_session = user_sessions[0]
    elif not active_session:
        # Create first initial session
        first_scan = user_scans[0] if user_scans else None
        active_session = ChatSession(
            user_id=current_user.id,
            scan_id=first_scan.id if first_scan else None,
            title="Forensic Consultation" if not first_scan else f"Scan #{first_scan.scan_uuid[:8]}"
        )
        db.session.add(active_session)
        db.session.commit()
        init_msg = ChatMessage(
            session_id=active_session.id,
            sender="assistant",
            content="Welcome to the **FaceGuard AI Forensic Assistant**! Ask me any question regarding your deepfake classification verdicts, Grad-CAM heatmaps, 2D-FFT frequency distributions, or Error Level Analysis findings.",
            source_attribution="forensic_engine"
        )
        db.session.add(init_msg)
        db.session.commit()
        # Refresh user sessions
        user_sessions = [active_session]

    return render_template(
        "chat/index.html",
        active_page="chat",
        active_session=active_session,
        user_sessions=user_sessions,
        user_scans=user_scans
    )

@chat_bp.route("/new", methods=["POST"])
@login_required
def create_new_session():
    """Explicitly initializes a new chat session"""
    scan_uuid = request.form.get("scan_uuid", "").strip()
    scan = None
    title = "New Forensic Consultation"

    if scan_uuid:
        scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first()
        if scan:
            title = f"Investigation: {scan.original_filename[:18]}"

    session = ChatSession(
        user_id=current_user.id,
        scan_id=scan.id if scan else None,
        title=title
    )
    db.session.add(session)
    db.session.commit()

    intro_text = "New forensic session initiated. "
    if scan:
        intro_text += f"Context attached to **`{scan.original_filename}`** ({scan.overall_prediction}, {scan.overall_confidence:.1f}%). How can I assist you with this file?"
    else:
        intro_text += "Select an investigation scan from the left panel to contextualize your inquiry, or ask general questions about biometric security."

    init_msg = ChatMessage(
        session_id=session.id,
        sender="assistant",
        content=intro_text,
        source_attribution="forensic_engine"
    )
    db.session.add(init_msg)
    db.session.commit()

    return redirect(url_for("chat.chat_index", session_uuid=session.session_uuid))

@chat_bp.route("/api/send", methods=["POST"])
@login_required
def api_send_message():
    """Processes incoming chat message and returns scientifically grounded explanation"""
    data = request.get_json(silent=True) or request.form
    session_uuid = data.get("session_uuid", "").strip()
    query_text = data.get("message", "").strip()

    if not query_text:
        return jsonify({"status": "error", "message": "Message content cannot be empty."}), 400

    session = ChatSession.query.filter_by(session_uuid=session_uuid, user_id=current_user.id).first()
    if not session:
        return jsonify({"status": "error", "message": "Chat session not found or unauthorized."}), 404

    # 1. Store User Message
    user_msg = ChatMessage(
        session_id=session.id,
        sender="user",
        content=query_text,
        source_attribution="user"
    )
    db.session.add(user_msg)

    # 2. Generate Forensic Response
    reply_text, source_attr = generate_chat_response(
        query_text=query_text,
        scan=session.scan,
        user_name=current_user.full_name
    )

    # 3. Store Assistant Message
    assistant_msg = ChatMessage(
        session_id=session.id,
        sender="assistant",
        content=reply_text,
        source_attribution=source_attr
    )
    db.session.add(assistant_msg)

    session.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "status": "success",
        "reply": reply_text,
        "source": source_attr,
        "timestamp": assistant_msg.created_at.strftime("%H:%M UTC")
    })

@chat_bp.route("/session/<session_uuid>/delete", methods=["POST"])
@login_required
def delete_session(session_uuid):
    """Deletes a chat session belonging to current user"""
    session = ChatSession.query.filter_by(session_uuid=session_uuid, user_id=current_user.id).first_or_404()
    db.session.delete(session)
    db.session.commit()
    flash("Forensic chat session removed.", "info")
    return redirect(url_for("chat.chat_index"))
