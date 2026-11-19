"""
FACEGUARD AI - Detection Comparison Studio Engine
Module: faceguard/core/comparator.py
"""
import os
import uuid
import cv2
import numpy as np
from faceguard.core.detector import get_predictor
from faceguard.core.gradcam import GradCAM
from faceguard.core.forensics import inspect_file_properties, extract_exif_metadata
from faceguard.core.risk import compute_risk_assessment

def compare_two_images(img_a_path, img_b_path, upload_folder, name_a="Image A", name_b="Image B"):
    """
    Executes comprehensive side-by-side comparative analysis between two images:
    1. Independent CNN inference & confidence scoring
    2. Synchronized Grad-CAM explainability heatmaps
    3. Multi-domain forensic signal comparison (Sensor noise, FFT, ELA, EXIF)
    4. AI Risk Assessment score comparison
    5. Visual pixel delta difference map
    6. Technical divergence metrics
    """
    predictor = get_predictor()

    # 1. CNN Inferences
    res_a = predictor.predict(img_a_path, mode="standard", save_artifacts=True)
    res_b = predictor.predict(img_b_path, mode="standard", save_artifacts=True)

    # 2. Grad-CAM Explanations
    gradcam = GradCAM(predictor.model)
    face_a_path = res_a.get("face_image_path")
    face_b_path = res_b.get("face_image_path")

    cam_a_filename = None
    cam_b_filename = None

    if face_a_path and os.path.exists(face_a_path):
        try:
            bgr_face_a = cv2.imread(face_a_path)
            if bgr_face_a is not None:
                target_cls = 0 if res_a["prediction"] == "FAKE" else 1
                cam_a_dict = gradcam.generate(bgr_face_a, target_class=target_cls)
                cam_a_id = f"cam_comp_a_{uuid.uuid4().hex[:10]}.jpg"
                cv2.imwrite(os.path.join(upload_folder, cam_a_id), cam_a_dict["overlay_bgr"])
                cam_a_filename = cam_a_id
        except Exception:
            pass

    if face_b_path and os.path.exists(face_b_path):
        try:
            bgr_face_b = cv2.imread(face_b_path)
            if bgr_face_b is not None:
                target_cls = 0 if res_b["prediction"] == "FAKE" else 1
                cam_b_dict = gradcam.generate(bgr_face_b, target_class=target_cls)
                cam_b_id = f"cam_comp_b_{uuid.uuid4().hex[:10]}.jpg"
                cv2.imwrite(os.path.join(upload_folder, cam_b_id), cam_b_dict["overlay_bgr"])
                cam_b_filename = cam_b_id
        except Exception:
            pass

    # 3. File Properties & EXIF
    props_a = inspect_file_properties(img_a_path, name_a)
    props_b = inspect_file_properties(img_b_path, name_b)
    exif_a = extract_exif_metadata(img_a_path)
    exif_b = extract_exif_metadata(img_b_path)

    # 4. Risk Assessments
    forensics_a = res_a.get("forensics", {})
    forensics_b = res_b.get("forensics", {})

    risk_a = compute_risk_assessment(
        cnn_prediction=res_a["prediction"],
        cnn_confidence=res_a["confidence"],
        sensor_variance=forensics_a.get("sensor_noise_variance", 50.0) or 50.0,
        fft_ratio=forensics_a.get("frequency_fft_ratio", 0.72) or 0.72,
        ela_uniformity=forensics_a.get("ela_uniformity", 1.2) or 1.2,
        chroma_score=forensics_a.get("chromatic_coherence", 0.88) or 0.88,
        has_exif=exif_a["has_exif"],
        face_count=res_a.get("face_count", 0)
    )

    risk_b = compute_risk_assessment(
        cnn_prediction=res_b["prediction"],
        cnn_confidence=res_b["confidence"],
        sensor_variance=forensics_b.get("sensor_noise_variance", 50.0) or 50.0,
        fft_ratio=forensics_b.get("frequency_fft_ratio", 0.72) or 0.72,
        ela_uniformity=forensics_b.get("ela_uniformity", 1.2) or 1.2,
        chroma_score=forensics_b.get("chromatic_coherence", 0.88) or 0.88,
        has_exif=exif_b["has_exif"],
        face_count=res_b.get("face_count", 0)
    )

    # 5. Visual Pixel Delta Map (Resized to common dimension)
    bgr_a = cv2.imread(img_a_path)
    bgr_b = cv2.imread(img_b_path)
    diff_filename = None
    mean_pixel_diff = 0.0

    if bgr_a is not None and bgr_b is not None:
        target_h, target_w = 400, 400
        resized_a = cv2.resize(bgr_a, (target_w, target_h))
        resized_b = cv2.resize(bgr_b, (target_w, target_h))
        diff_raw = cv2.absdiff(resized_a, resized_b)
        diff_scaled = cv2.convertScaleAbs(diff_raw, alpha=5.0)
        diff_gray = cv2.cvtColor(diff_scaled, cv2.COLOR_BGR2GRAY)
        diff_heatmap = cv2.applyColorMap(diff_gray, cv2.COLORMAP_MAGMA)

        diff_id = f"diff_map_{uuid.uuid4().hex[:10]}.jpg"
        diff_path = os.path.join(upload_folder, diff_id)
        cv2.imwrite(diff_path, diff_heatmap)
        diff_filename = diff_id
        mean_pixel_diff = round(float(np.mean(diff_gray)), 2)

    # 6. Divergence Metrics
    conf_delta = round(abs(res_a["confidence"] - res_b["confidence"]), 1)
    risk_delta = round(abs(risk_a["risk_score"] - risk_b["risk_score"]), 1)
    concordant = (res_a["prediction"] == res_b["prediction"])

    if concordant:
        summary = f"Concordant verdict: Both images classified as {res_a['prediction']} (Risk Score difference: {risk_delta} points)."
    else:
        summary = f"Divergent verdict: Image A classified as {res_a['prediction']} ({res_a['confidence']}%), while Image B classified as {res_b['prediction']} ({res_b['confidence']}%)."

    return {
        "image_a": {
            "name": name_a,
            "filename": os.path.basename(img_a_path),
            "prediction": res_a["prediction"],
            "confidence": res_a["confidence"],
            "face_crop": os.path.basename(face_a_path) if face_a_path else None,
            "gradcam": cam_a_filename,
            "props": props_a,
            "exif": exif_a,
            "risk": risk_a,
            "forensics": forensics_a
        },
        "image_b": {
            "name": name_b,
            "filename": os.path.basename(img_b_path),
            "prediction": res_b["prediction"],
            "confidence": res_b["confidence"],
            "face_crop": os.path.basename(face_b_path) if face_b_path else None,
            "gradcam": cam_b_filename,
            "props": props_b,
            "exif": exif_b,
            "risk": risk_b,
            "forensics": forensics_b
        },
        "diff_map": diff_filename,
        "mean_pixel_diff": mean_pixel_diff,
        "conf_delta": conf_delta,
        "risk_delta": risk_delta,
        "concordant": concordant,
        "summary": summary
    }
