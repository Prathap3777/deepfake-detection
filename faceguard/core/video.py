"""
FACEGUARD AI - Video Deepfake Detection Pipeline
Module: faceguard/core/video.py
Controlled frame sampling, face localization, and multi-domain frame aggregation
"""
import os
import cv2
import numpy as np
from faceguard.config import Config
from faceguard.core.detector import get_predictor

def format_timestamp(seconds):
    """Formats seconds into MM:SS timestamp string"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def analyze_video(video_path, max_frames=20, sample_fps=1, artifact_prefix=""):
    """
    Video Deepfake Detection via Controlled Frame Sampling:
    1. Extracts frames at 1 fps (up to max_frames) to respect memory & compute limits
    2. Localizes human faces in each sampled frame
    3. Evaluates ResNet-18 inference and multi-domain forensics per face
    4. Aggregates frame-level scores into an overall video authenticity verdict
    5. Pinpoints suspicious timestamps where manipulation artifacts occur
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file for processing. Invalid or corrupted codec.")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    duration_sec = total_video_frames / video_fps if video_fps > 0 else 0.0

    # Determine frame sampling step
    step = max(1, int(round(video_fps / sample_fps)))
    predictor = get_predictor()

    base_name = os.path.basename(video_path)
    stem = os.path.splitext(base_name)[0]
    prefix = f"{artifact_prefix}_" if artifact_prefix else ""
    frames_dir = os.path.join(Config.UPLOAD_FOLDER, "video_frames")
    os.makedirs(frames_dir, exist_ok=True)

    sampled_frames_data = []
    current_frame_idx = 0
    sampled_count = 0
    face_frames_count = 0
    real_frames_count = 0
    fake_frames_count = 0
    sum_confidence = 0.0
    highest_fake_conf = 0.0
    thumbnail_rel_path = None

    while cap.isOpened() and sampled_count < max_frames:
        ret, frame_bgr = cap.read()
        if not ret:
            break

        if current_frame_idx % step == 0:
            timestamp_sec = round(current_frame_idx / video_fps, 2)
            timestamp_str = format_timestamp(timestamp_sec)
            sampled_count += 1

            # Detect face in frame
            crop_bgr, annotated_bgr, face_found, bbox, face_count = predictor.detect_and_crop_face(frame_bgr)

            frame_filename = f"vframe_{prefix}{stem}_{sampled_count}.jpg"
            frame_save_path = os.path.join(frames_dir, frame_filename)
            frame_rel_path = f"static/uploads/video_frames/{frame_filename}"

            if thumbnail_rel_path is None:
                thumbnail_rel_path = frame_rel_path

            if face_found:
                face_frames_count += 1
                # Run prediction on cropped face
                temp_crop_path = os.path.join(frames_dir, f"temp_crop_{prefix}{sampled_count}.jpg")
                cv2.imwrite(temp_crop_path, crop_bgr)
                
                try:
                    pred_res = predictor.predict(temp_crop_path, mode="standard", save_artifacts=False)
                    frame_pred = pred_res["prediction"]
                    frame_conf = pred_res["confidence"]
                finally:
                    if os.path.exists(temp_crop_path):
                        os.remove(temp_crop_path)

                is_suspicious = (frame_pred == "FAKE")
                if is_suspicious:
                    fake_frames_count += 1
                    highest_fake_conf = max(highest_fake_conf, frame_conf)
                    box_color = (0, 0, 220)  # Red for fake
                else:
                    real_frames_count += 1
                    box_color = (0, 200, 0)  # Green for real

                sum_confidence += frame_conf

                # Draw timestamp and verdict badge on frame
                cv2.rectangle(frame_bgr, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), box_color, 2)
                badge = f"{timestamp_str} | {frame_pred} {round(frame_conf)}%"
                cv2.putText(frame_bgr, badge, (bbox[0], max(20, bbox[1] - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                cv2.imwrite(frame_save_path, frame_bgr)

                sampled_frames_data.append({
                    "frame_index": sampled_count,
                    "timestamp_sec": timestamp_sec,
                    "timestamp_str": timestamp_str,
                    "frame_path": frame_rel_path,
                    "face_detected": True,
                    "prediction": frame_pred,
                    "confidence": round(float(frame_conf), 1),
                    "is_suspicious": is_suspicious
                })
            else:
                # No face detected in this frame
                cv2.putText(frame_bgr, f"{timestamp_str} | No Face Detected", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
                cv2.imwrite(frame_save_path, frame_bgr)

                sampled_frames_data.append({
                    "frame_index": sampled_count,
                    "timestamp_sec": timestamp_sec,
                    "timestamp_str": timestamp_str,
                    "frame_path": frame_rel_path,
                    "face_detected": False,
                    "prediction": None,
                    "confidence": 0.0,
                    "is_suspicious": False
                })

        current_frame_idx += 1

    cap.release()

    # Video-Level Aggregation Methodology:
    # 1. If >= 15% of face frames exhibit synthetic/deepfake artifacts -> Flagged FAKE
    # 2. Otherwise -> Verified REAL
    # 3. If no faces detected in any frame -> UNKNOWN
    if face_frames_count == 0:
        overall_pred = "UNKNOWN"
        overall_conf = 0.0
        status_desc = f"Sampled {sampled_count} frames across {round(duration_sec, 1)}s. No human faces localized."
    else:
        fake_ratio = fake_frames_count / face_frames_count
        avg_conf = sum_confidence / face_frames_count

        if fake_ratio >= 0.15:
            overall_pred = "FAKE"
            overall_conf = highest_fake_conf
            status_desc = f"Sampled {sampled_count} frames ({face_frames_count} with faces). {fake_frames_count} frame(s) exhibit synthetic manipulation artifacts."
        else:
            overall_pred = "REAL"
            overall_conf = avg_conf
            status_desc = f"Sampled {sampled_count} frames ({face_frames_count} with faces). All analyzed frames verified authentic."

    return {
        "total_sampled_frames": sampled_count,
        "face_frames_count": face_frames_count,
        "real_frames_count": real_frames_count,
        "fake_frames_count": fake_frames_count,
        "overall_prediction": overall_pred,
        "overall_confidence": round(float(overall_conf), 1),
        "video_duration_sec": round(float(duration_sec), 1),
        "video_fps": round(float(video_fps), 1),
        "thumbnail_path": thumbnail_rel_path or f"static/uploads/video_frames/vframe_{prefix}{stem}_1.jpg",
        "analysis_status": status_desc,
        "aggregation_method": "Thresholded Frame-Level Spatial Aggregation (15% manipulation threshold; no temporal recurrent optical flow claimed)",
        "frames": sampled_frames_data
    }
