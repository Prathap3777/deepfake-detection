"""
FACEGUARD AI - Deepfake Detection Controller
Module: faceguard/blueprints/detect/__init__.py
"""
import os
import uuid
import cv2
from werkzeug.utils import secure_filename
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from faceguard.config import Config
from faceguard.extensions import db
from faceguard.models.scan import Scan, FaceResult, VideoFrame
from faceguard.core.detector import get_predictor
from faceguard.core.gradcam import GradCAM
from faceguard.core.video import analyze_video
from faceguard.utils.security import log_audit

detect_bp = Blueprint("detect", __name__)

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

@detect_bp.route("/image", methods=["GET", "POST"])
@login_required
def image_page():
    """Single Face Deepfake Detection Route"""
    if request.method == "POST":
        file = request.files.get("image") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No image file uploaded."}), 400
            flash("Please choose a valid JPG or PNG image to analyze.", "error")
            return redirect(url_for("detect.image_page"))

        if not allowed_file(file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            err_msg = f"Unsupported file type. Supported formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.image_page"))

        mode = request.form.get("mode", "standard").strip().lower()
        if mode not in ("standard", "portrait"):
            mode = "standard"

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "upload.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        saved_filename = f"scan_{scan_uuid[:12]}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        try:
            predictor = get_predictor()
            result = predictor.predict(
                filepath,
                mode=mode,
                save_artifacts=True,
                artifact_prefix=scan_uuid[:8]
            )

            from faceguard.core.risk import compute_risk_assessment
            forensics = result.get("forensics", {})
            risk_info = compute_risk_assessment(
                cnn_prediction=result.get("prediction", "REAL"),
                cnn_confidence=result.get("confidence", 0.0),
                sensor_variance=forensics.get("sensor_noise_variance", 50.0) or 50.0,
                fft_ratio=forensics.get("frequency_fft_ratio", 0.72) or 0.72,
                ela_uniformity=forensics.get("ela_uniformity", 1.2) or 1.2,
                chroma_score=forensics.get("chromatic_coherence", 0.88) or 0.88,
                has_exif=False,
                face_count=result.get("face_count", 0)
            )
            result["risk_assessment"] = risk_info

            scan = Scan(
                scan_uuid=scan_uuid,
                user_id=current_user.id,
                media_type="image",
                original_filename=orig_filename,
                saved_filename=saved_filename,
                sha256=result.get("sha256"),
                face_count=result.get("face_count", 0),
                overall_prediction=result.get("prediction"),
                overall_confidence=result.get("confidence", 0.0),
                real_probability=result.get("real_probability", 0.0),
                fake_probability=result.get("fake_probability", 0.0),
                risk_score=risk_info["risk_score"],
                review_priority=risk_info["review_priority"],
                annotated_path=result.get("annotated_image_path"),
                analysis_mode=mode,
                analysis_status=result.get("analysis_status"),
                status="completed"
            )
            db.session.add(scan)
            db.session.flush()

            bbox = result.get("bounding_box") or [0, 0, 0, 0]
            forensics = result.get("forensics", {})
            face_res = FaceResult(
                scan_id=scan.id,
                face_index=1,
                bbox_x=bbox[0] if len(bbox) > 0 else 0,
                bbox_y=bbox[1] if len(bbox) > 1 else 0,
                bbox_w=bbox[2] if len(bbox) > 2 else 0,
                bbox_h=bbox[3] if len(bbox) > 3 else 0,
                prediction=result.get("prediction"),
                confidence=result.get("confidence", 0.0),
                real_probability=result.get("real_probability", 0.0),
                fake_probability=result.get("fake_probability", 0.0),
                face_crop_path=result.get("face_image_path"),
                ela_path=result.get("ela_image_path"),
                fft_path=result.get("fft_image_path"),
                sensor_variance=forensics.get("sensor_noise_variance"),
                fft_ratio=forensics.get("frequency_fft_ratio"),
                ela_mean=forensics.get("ela_mean"),
                chroma_score=forensics.get("chromatic_coherence")
            )
            db.session.add(face_res)
            db.session.commit()

            log_audit("image_scan_completed", f"Scan {scan.scan_uuid[:8]} - {scan.overall_prediction} ({scan.overall_confidence}%)")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "scan_uuid": scan.scan_uuid,
                    "result": result
                })

            return render_template(
                "detect/image.html",
                active_page="detect_image",
                result=result,
                scan=scan
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Image detection error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Analysis failed: {str(e)}"}), 500
            flash(f"Image analysis failed: {str(e)}", "error")
            return redirect(url_for("detect.image_page"))

    return render_template("detect/image.html", active_page="detect_image", result=None, scan=None)

@detect_bp.route("/multi-face", methods=["GET", "POST"])
@login_required
def multi_face_page():
    """Multiple Face Detection Route"""
    if request.method == "POST":
        file = request.files.get("image") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No image file uploaded."}), 400
            flash("Please choose a valid JPG or PNG group image to analyze.", "error")
            return redirect(url_for("detect.multi_face_page"))

        if not allowed_file(file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            err_msg = f"Unsupported file type. Supported formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.multi_face_page"))

        mode = request.form.get("mode", "standard").strip().lower()
        if mode not in ("standard", "portrait"):
            mode = "standard"

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "group_upload.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        saved_filename = f"multi_{scan_uuid[:12]}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        try:
            predictor = get_predictor()
            result = predictor.predict_multi_face(
                filepath,
                mode=mode,
                save_artifacts=True,
                artifact_prefix=scan_uuid[:8]
            )

            scan = Scan(
                scan_uuid=scan_uuid,
                user_id=current_user.id,
                media_type="image",
                original_filename=orig_filename,
                saved_filename=saved_filename,
                sha256=result.get("sha256"),
                face_count=result.get("face_count", 0),
                overall_prediction=result.get("overall_prediction"),
                overall_confidence=result.get("overall_confidence", 0.0),
                annotated_path=result.get("annotated_image_path"),
                analysis_mode=f"multi-face ({mode})",
                analysis_status=result.get("analysis_status"),
                status="completed"
            )
            db.session.add(scan)
            db.session.flush()

            for f_info in result.get("faces", []):
                bbox = f_info.get("bounding_box", [0, 0, 0, 0])
                forensics = f_info.get("forensics", {})
                face_res = FaceResult(
                    scan_id=scan.id,
                    face_index=f_info.get("face_index", 1),
                    bbox_x=bbox[0],
                    bbox_y=bbox[1],
                    bbox_w=bbox[2],
                    bbox_h=bbox[3],
                    prediction=f_info.get("prediction"),
                    confidence=f_info.get("confidence", 0.0),
                    real_probability=f_info.get("real_probability", 0.0),
                    fake_probability=f_info.get("fake_probability", 0.0),
                    face_crop_path=f_info.get("crop_path"),
                    sensor_variance=forensics.get("sensor_noise_variance"),
                    fft_ratio=forensics.get("frequency_fft_ratio"),
                    ela_mean=forensics.get("ela_mean"),
                    chroma_score=forensics.get("chromatic_coherence")
                )
                db.session.add(face_res)

            db.session.commit()
            log_audit("multi_face_scan_completed", f"Scan {scan.scan_uuid[:8]} - {scan.face_count} faces - {scan.overall_prediction}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "scan_uuid": scan.scan_uuid,
                    "result": result
                })

            return render_template(
                "detect/multi_face.html",
                active_page="multi_face",
                result=result,
                scan=scan
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Multi-face detection error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Multi-face analysis failed: {str(e)}"}), 500
            flash(f"Multi-face analysis failed: {str(e)}", "error")
            return redirect(url_for("detect.multi_face_page"))

    return render_template("detect/multi_face.html", active_page="multi_face", result=None, scan=None)

@detect_bp.route("/gradcam", methods=["GET", "POST"])
@login_required
def gradcam_page():
    """Grad-CAM Explainable AI Visualization Route"""
    if request.method == "POST":
        file = request.files.get("image") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No image file uploaded."}), 400
            flash("Please choose a valid JPG or PNG image to generate a Grad-CAM heatmap.", "error")
            return redirect(url_for("detect.gradcam_page"))

        if not allowed_file(file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            err_msg = f"Unsupported file type. Supported formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.gradcam_page"))

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "gradcam_upload.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        saved_filename = f"gradcam_{scan_uuid[:12]}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        try:
            predictor = get_predictor()
            img_bgr = cv2.imread(filepath)
            if img_bgr is None:
                raise ValueError("Could not read uploaded image.")

            crop_bgr, annotated_bgr, face_found, bbox, face_count = predictor.detect_and_crop_face(img_bgr)

            gradcam_engine = GradCAM(predictor.model)
            cam_data = gradcam_engine.generate(crop_bgr)

            stem = scan_uuid[:8]
            crop_filename = f"gradcam_crop_{stem}.jpg"
            jet_filename = f"gradcam_jet_{stem}.jpg"
            overlay_filename = f"gradcam_overlay_{stem}.jpg"

            crop_path = os.path.join(Config.UPLOAD_FOLDER, crop_filename)
            jet_path = os.path.join(Config.UPLOAD_FOLDER, jet_filename)
            overlay_path = os.path.join(Config.UPLOAD_FOLDER, overlay_filename)

            cv2.imwrite(crop_path, crop_bgr)
            cv2.imwrite(jet_path, cam_data["heatmap_jet"])
            cv2.imwrite(overlay_path, cam_data["overlay_bgr"])

            pred_result = predictor.predict(filepath, save_artifacts=False)

            scan = Scan(
                scan_uuid=scan_uuid,
                user_id=current_user.id,
                media_type="image",
                original_filename=orig_filename,
                saved_filename=saved_filename,
                sha256=pred_result.get("sha256"),
                face_count=1 if face_found else 0,
                overall_prediction=pred_result.get("prediction"),
                overall_confidence=pred_result.get("confidence", 0.0),
                annotated_path=f"static/uploads/{overlay_filename}",
                analysis_mode="gradcam-xai",
                analysis_status=cam_data["focus_description"],
                status="completed"
            )
            db.session.add(scan)
            db.session.flush()

            face_res = FaceResult(
                scan_id=scan.id,
                face_index=1,
                bbox_x=bbox[0] if len(bbox) > 0 else 0,
                bbox_y=bbox[1] if len(bbox) > 1 else 0,
                bbox_w=bbox[2] if len(bbox) > 2 else 0,
                bbox_h=bbox[3] if len(bbox) > 3 else 0,
                prediction=pred_result.get("prediction"),
                confidence=pred_result.get("confidence", 0.0),
                face_crop_path=f"static/uploads/{crop_filename}",
                gradcam_path=f"static/uploads/{overlay_filename}",
                ela_path=None,
                fft_path=f"static/uploads/{jet_filename}"
            )
            db.session.add(face_res)
            db.session.commit()

            log_audit("gradcam_generated", f"Scan {scan.scan_uuid[:8]} - Class: {cam_data['class_name']} - {cam_data['primary_focus']}")

            result = {
                "scan_uuid": scan_uuid,
                "face_detected": face_found,
                "crop_path": f"static/uploads/{crop_filename}",
                "jet_path": f"static/uploads/{jet_filename}",
                "overlay_path": f"static/uploads/{overlay_filename}",
                "prediction": pred_result.get("prediction"),
                "confidence": pred_result.get("confidence"),
                "primary_focus": cam_data["primary_focus"],
                "focus_description": cam_data["focus_description"],
                "zone_distribution": cam_data["zone_distribution"],
                "target_class_name": cam_data["class_name"]
            }

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": True, "result": result})

            return render_template(
                "detect/gradcam.html",
                active_page="gradcam",
                result=result,
                scan=scan
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Grad-CAM generation error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Grad-CAM generation failed: {str(e)}"}), 500
            flash(f"Grad-CAM generation failed: {str(e)}", "error")
            return redirect(url_for("detect.gradcam_page"))

    return render_template("detect/gradcam.html", active_page="gradcam", result=None, scan=None)

@detect_bp.route("/video", methods=["GET", "POST"])
@login_required
def video_page():
    """Video Deepfake Detection Route"""
    if request.method == "POST":
        file = request.files.get("video") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No video file uploaded."}), 400
            flash("Please choose a valid MP4, AVI, or MOV video to analyze.", "error")
            return redirect(url_for("detect.video_page"))

        if not allowed_file(file.filename, Config.ALLOWED_VIDEO_EXTENSIONS):
            err_msg = f"Unsupported video format. Supported formats: {', '.join(Config.ALLOWED_VIDEO_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.video_page"))

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "video_upload.mp4"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "mp4"
        saved_filename = f"video_{scan_uuid[:12]}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        try:
            # Sample frames at 1 fps, up to 20 frames for memory safety
            result = analyze_video(
                filepath,
                max_frames=20,
                sample_fps=1,
                artifact_prefix=scan_uuid[:8]
            )

            # Persist Scan record for video
            scan = Scan(
                scan_uuid=scan_uuid,
                user_id=current_user.id,
                media_type="video",
                original_filename=orig_filename,
                saved_filename=saved_filename,
                face_count=result.get("face_frames_count", 0),
                overall_prediction=result.get("overall_prediction"),
                overall_confidence=result.get("overall_confidence", 0.0),
                annotated_path=result.get("thumbnail_path"),
                analysis_mode="video-frames",
                analysis_status=result.get("analysis_status"),
                status="completed"
            )
            db.session.add(scan)
            db.session.flush()

            # Persist VideoFrame records
            for f_info in result.get("frames", []):
                v_frame = VideoFrame(
                    scan_id=scan.id,
                    frame_index=f_info["frame_index"],
                    timestamp_sec=f_info["timestamp_sec"],
                    frame_path=f_info["frame_path"],
                    face_detected=f_info["face_detected"],
                    prediction=f_info.get("prediction"),
                    confidence=f_info.get("confidence", 0.0),
                    is_suspicious=f_info.get("is_suspicious", False)
                )
                db.session.add(v_frame)

            db.session.commit()
            log_audit("video_scan_completed", f"Scan {scan.scan_uuid[:8]} - {scan.face_count} face frames - {scan.overall_prediction}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "scan_uuid": scan.scan_uuid,
                    "result": result
                })

            return render_template(
                "detect/video.html",
                active_page="detect_video",
                result=result,
                scan=scan
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Video analysis error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Video analysis failed: {str(e)}"}), 500
            flash(f"Video analysis failed: {str(e)}", "error")
            return redirect(url_for("detect.video_page"))

    return render_template("detect/video.html", active_page="detect_video", result=None, scan=None)

@detect_bp.route("/forensics", methods=["GET", "POST"])
@login_required
def forensics_page():
    """AI Forensic Intelligence Center - Deep Multi-Domain Photographic Inspection"""
    if request.method == "POST":
        file = request.files.get("image") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No image file uploaded."}), 400
            flash("Please upload a valid photographic image for forensic examination.", "error")
            return redirect(url_for("detect.forensics_page"))

        if not allowed_file(file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            err_msg = f"Unsupported file type. Supported formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.forensics_page"))

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "evidence.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        saved_filename = f"forensic_{scan_uuid[:12]}.{ext}"
        saved_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_filename)

        try:
            file.save(saved_path)

            from faceguard.core.forensics import analyze_full_forensics
            forensics_report = analyze_full_forensics(saved_path, orig_filename, current_app.config["UPLOAD_FOLDER"])

            log_audit("forensic_audit_performed", f"Forensic audit on {orig_filename}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "filename": saved_filename,
                    "report": forensics_report
                })

            return render_template(
                "detect/forensics.html",
                active_page="detect_forensics",
                report=forensics_report,
                saved_filename=saved_filename,
                orig_filename=orig_filename
            )

        except Exception as e:
            current_app.logger.error(f"Forensic audit error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Forensic analysis failed: {str(e)}"}), 500
            flash(f"Forensic analysis failed: {str(e)}", "error")
            return redirect(url_for("detect.forensics_page"))

    # Also support inspecting an existing scan via ?scan=<uuid>
    scan_uuid = request.args.get("scan")
    if scan_uuid:
        scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first()
        if scan and scan.media_type == "image":
            target_path = os.path.join(current_app.config["UPLOAD_FOLDER"], scan.saved_filename)
            if os.path.exists(target_path):
                from faceguard.core.forensics import analyze_full_forensics
                forensics_report = analyze_full_forensics(target_path, scan.original_filename, current_app.config["UPLOAD_FOLDER"])
                return render_template(
                    "detect/forensics.html",
                    active_page="detect_forensics",
                    report=forensics_report,
                    saved_filename=scan.saved_filename,
                    orig_filename=scan.original_filename,
                    source_scan=scan
                )

    return render_template("detect/forensics.html", active_page="detect_forensics", report=None)

@detect_bp.route("/risk", methods=["GET", "POST"])
@login_required
def risk_page():
    """AI Risk Assessment Score & Review Priority Module"""
    if request.method == "POST":
        file = request.files.get("image") or request.files.get("file")
        if not file or file.filename.strip() == "":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": "No image file uploaded."}), 400
            flash("Please choose an image file for AI Risk Assessment.", "error")
            return redirect(url_for("detect.risk_page"))

        if not allowed_file(file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            err_msg = f"Unsupported file type. Supported formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS).upper()}."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("detect.risk_page"))

        scan_uuid = str(uuid.uuid4())
        orig_filename = secure_filename(file.filename) or "upload.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        saved_filename = f"risk_{scan_uuid[:12]}.{ext}"
        saved_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_filename)

        try:
            file.save(saved_path)

            from faceguard.core.detector import get_predictor
            from faceguard.core.risk import compute_risk_assessment
            predictor = get_predictor()
            pred_res = predictor.predict(saved_path, mode="standard", save_artifacts=False)

            forensics = pred_res.get("forensics", {})
            risk_info = compute_risk_assessment(
                cnn_prediction=pred_res.get("prediction", "REAL"),
                cnn_confidence=pred_res.get("confidence", 0.0),
                sensor_variance=forensics.get("sensor_noise_variance", 50.0) or 50.0,
                fft_ratio=forensics.get("frequency_fft_ratio", 0.72) or 0.72,
                ela_uniformity=forensics.get("ela_uniformity", 1.2) or 1.2,
                chroma_score=forensics.get("chromatic_coherence", 0.88) or 0.88,
                has_exif=False,
                face_count=pred_res.get("face_count", 0)
            )

            log_audit("risk_assessment_computed", f"Risk score: {risk_info['risk_score']} ({risk_info['review_priority']}) for {orig_filename}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "filename": saved_filename,
                    "prediction": pred_res,
                    "risk": risk_info
                })

            return render_template(
                "detect/risk.html",
                active_page="detect_risk",
                risk=risk_info,
                prediction=pred_res,
                saved_filename=saved_filename,
                orig_filename=orig_filename
            )

        except Exception as e:
            current_app.logger.error(f"Risk assessment error: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "error": f"Risk assessment failed: {str(e)}"}), 500
            flash(f"Risk assessment failed: {str(e)}", "error")
            return redirect(url_for("detect.risk_page"))

    # Support inspecting past scan
    scan_uuid = request.args.get("scan")
    if scan_uuid:
        scan = Scan.query.filter_by(scan_uuid=scan_uuid, user_id=current_user.id).first()
        if scan:
            from faceguard.core.risk import compute_risk_assessment
            face_item = scan.faces[0] if scan.faces else None
            risk_info = compute_risk_assessment(
                cnn_prediction=scan.overall_prediction or "REAL",
                cnn_confidence=scan.overall_confidence or 0.0,
                sensor_variance=face_item.sensor_variance if face_item and face_item.sensor_variance else 50.0,
                fft_ratio=face_item.fft_ratio if face_item and face_item.fft_ratio else 0.72,
                ela_uniformity=1.2,
                chroma_score=face_item.chroma_score if face_item and face_item.chroma_score else 0.88,
                has_exif=False,
                face_count=scan.face_count,
                is_video=(scan.media_type == "video")
            )
            return render_template(
                "detect/risk.html",
                active_page="detect_risk",
                risk=risk_info,
                prediction={"prediction": scan.overall_prediction, "confidence": scan.overall_confidence},
                saved_filename=scan.saved_filename,
                orig_filename=scan.original_filename,
                source_scan=scan
            )

    return render_template("detect/risk.html", active_page="detect_risk", risk=None)

@detect_bp.route("/compare", methods=["GET", "POST"])
@login_required
def comparison_studio():
    """Detection Comparison Studio - Side-by-Side Image A vs Image B Forensics"""
    recent_user_scans = Scan.query.filter_by(user_id=current_user.id, media_type="image").order_by(Scan.created_at.desc()).limit(20).all()

    if request.method == "POST":
        file_a = request.files.get("image_a")
        file_b = request.files.get("image_b")
        scan_id_a = request.form.get("scan_id_a")
        scan_id_b = request.form.get("scan_id_b")

        path_a = None
        path_b = None
        name_a = "Image A"
        name_b = "Image B"

        # Resolve Image A
        if file_a and file_a.filename.strip():
            if not allowed_file(file_a.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
                flash("Image A has an unsupported file format.", "error")
                return redirect(url_for("detect.comparison_studio"))
            name_a = secure_filename(file_a.filename) or "Image_A.jpg"
            saved_a = f"comp_a_{uuid.uuid4().hex[:10]}_{name_a}"
            path_a = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_a)
            file_a.save(path_a)
        elif scan_id_a:
            s_a = Scan.query.filter_by(scan_uuid=scan_id_a, user_id=current_user.id).first()
            if s_a:
                path_a = os.path.join(current_app.config["UPLOAD_FOLDER"], s_a.saved_filename)
                name_a = s_a.original_filename

        # Resolve Image B
        if file_b and file_b.filename.strip():
            if not allowed_file(file_b.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
                flash("Image B has an unsupported file format.", "error")
                return redirect(url_for("detect.comparison_studio"))
            name_b = secure_filename(file_b.filename) or "Image_B.jpg"
            saved_b = f"comp_b_{uuid.uuid4().hex[:10]}_{name_b}"
            path_b = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_b)
            file_b.save(path_b)
        elif scan_id_b:
            s_b = Scan.query.filter_by(scan_uuid=scan_id_b, user_id=current_user.id).first()
            if s_b:
                path_b = os.path.join(current_app.config["UPLOAD_FOLDER"], s_b.saved_filename)
                name_b = s_b.original_filename

        if not path_a or not path_b or not os.path.exists(path_a) or not os.path.exists(path_b):
            flash("Please provide two valid images or historical scans to compare.", "warning")
            return redirect(url_for("detect.comparison_studio"))

        try:
            from faceguard.core.comparator import compare_two_images
            comp_result = compare_two_images(path_a, path_b, current_app.config["UPLOAD_FOLDER"], name_a, name_b)

            log_audit("comparison_performed", f"Compared {name_a} vs {name_b}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "comparison": comp_result
                })

            return render_template(
                "detect/comparison.html",
                active_page="detect_compare",
                comparison=comp_result,
                recent_scans=recent_user_scans
            )

        except Exception as e:
            current_app.logger.error(f"Comparison error: {str(e)}")
            flash(f"Comparison failed: {str(e)}", "error")
            return redirect(url_for("detect.comparison_studio"))

    return render_template(
        "detect/comparison.html",
        active_page="detect_compare",
        comparison=None,
        recent_scans=recent_user_scans
    )

@detect_bp.route("/compare/export", methods=["POST"])
@login_required
def export_comparison_pdf():
    """Generates and downloads a comparison PDF dossier"""
    try:
        import json
        from flask import send_file
        from faceguard.utils.pdf import generate_comparison_pdf
        data_json = request.form.get("comparison_data")
        if not data_json:
            flash("No comparison session data found to export.", "warning")
            return redirect(url_for("detect.comparison_studio"))

        comp_data = json.loads(data_json)
        pdf_path = generate_comparison_pdf(comp_data)
        return send_file(pdf_path, as_attachment=True, download_name="comparison_dossier.pdf")

    except Exception as e:
        current_app.logger.error(f"Failed to export comparison PDF: {str(e)}")
        flash(f"PDF compilation failed: {str(e)}", "error")
        return redirect(url_for("detect.comparison_studio"))

@detect_bp.route("/batch", methods=["GET", "POST"])
@login_required
def batch_page():
    """Batch Image Intelligence - Bulk Upload, Async Processing & Group Analytics"""
    from faceguard.models.batch import BatchJob
    user_batches = BatchJob.query.filter_by(user_id=current_user.id).order_by(BatchJob.created_at.desc()).limit(10).all()

    if request.method == "POST":
        files = request.files.getlist("images") or request.files.getlist("files")
        valid_files = [f for f in files if f and f.filename.strip()]

        if not valid_files:
            flash("Please choose at least one image file for batch analysis.", "warning")
            return redirect(url_for("detect.batch_page"))

        # Configurable limit: Max 20 files per batch for 512MB RAM budget safety
        MAX_BATCH_FILES = 20
        if len(valid_files) > MAX_BATCH_FILES:
            flash(f"Batch limit exceeded: You may upload a maximum of {MAX_BATCH_FILES} images per session.", "error")
            return redirect(url_for("detect.batch_page"))

        title = request.form.get("title", "").strip() or f"Batch Investigation ({len(valid_files)} items)"

        try:
            from faceguard.core.batch import process_batch_upload
            batch_job = process_batch_upload(current_user.id, valid_files, current_app.config["UPLOAD_FOLDER"], title)
            log_audit("batch_scan_completed", f"Batch {batch_job.batch_uuid[:8]} - {batch_job.total_files} items ({batch_job.threat_rate}% threats)")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "success": True,
                    "batch_uuid": batch_job.batch_uuid,
                    "redirect_url": url_for("detect.batch_detail_page", batch_uuid=batch_job.batch_uuid)
                })

            return redirect(url_for("detect.batch_detail_page", batch_uuid=batch_job.batch_uuid))

        except Exception as e:
            current_app.logger.error(f"Batch processing failed: {str(e)}")
            flash(f"Batch processing error: {str(e)}", "error")
            return redirect(url_for("detect.batch_page"))

    return render_template(
        "detect/batch.html",
        active_page="detect_batch",
        batch=None,
        user_batches=user_batches
    )

@detect_bp.route("/batch/<batch_uuid>")
@login_required
def batch_detail_page(batch_uuid):
    """View details, summary KPI widgets, and items breakdown for a specific batch"""
    from faceguard.models.batch import BatchJob
    batch = BatchJob.query.filter_by(batch_uuid=batch_uuid, user_id=current_user.id).first_or_404()
    user_batches = BatchJob.query.filter_by(user_id=current_user.id).order_by(BatchJob.created_at.desc()).limit(10).all()

    return render_template(
        "detect/batch.html",
        active_page="detect_batch",
        batch=batch,
        user_batches=user_batches
    )

@detect_bp.route("/batch/<batch_uuid>/report")
@login_required
def export_batch_pdf(batch_uuid):
    """Generates and downloads a combined PDF report for the batch job"""
    from flask import send_file
    from faceguard.models.batch import BatchJob
    from faceguard.utils.pdf import generate_batch_pdf

    batch = BatchJob.query.filter_by(batch_uuid=batch_uuid, user_id=current_user.id).first_or_404()
    pdf_path = generate_batch_pdf(batch)
    return send_file(pdf_path, as_attachment=True, download_name=f"batch_report_{batch.batch_uuid[:8]}.pdf")

@detect_bp.route("/batch/api/status/<batch_uuid>")
@login_required
def batch_status_api(batch_uuid):
    """REST API polling endpoint for real-time batch progress"""
    from faceguard.models.batch import BatchJob
    batch = BatchJob.query.filter_by(batch_uuid=batch_uuid, user_id=current_user.id).first_or_404()

    return jsonify({
        "success": True,
        "batch_uuid": batch.batch_uuid,
        "status": batch.status,
        "total_files": batch.total_files,
        "processed_files": batch.processed_files,
        "real_count": batch.real_count,
        "fake_count": batch.fake_count,
        "threat_rate": batch.threat_rate
    })
