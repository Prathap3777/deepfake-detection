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
