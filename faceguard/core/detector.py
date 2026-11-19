"""
FACEGUARD AI - Deepfake & Face Authenticity Inference Engine
Module: faceguard/core/detector.py
Combines ResNet-18 Deep Residual Representations with Multi-Domain Digital Forensics
"""
import os
import json
import hashlib
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
from faceguard.config import Config, BASE_DIR
from faceguard.core.forensics import extract_forensic_signals

IMAGE_SIZE = (128, 128)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Optimize memory consumption for cloud deployment (512MB RAM budget)
torch.set_grad_enabled(False)
torch.set_num_threads(1)

class DeepfakeDetectorNet(nn.Module):
    """Deep residual neural network backbone for facial manipulation detection"""
    def __init__(self, num_classes=2, pretrained=False):
        super(DeepfakeDetectorNet, self).__init__()
        from torchvision import models
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        self.backbone = models.resnet18(weights=weights)
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)

class DeepfakePredictor:
    """Production Inference Engine for Single and Multi-Domain Forensic Face Analysis"""
    def __init__(self, model_path=None, cascade_path=None):
        self.device = DEVICE
        self.model_path = model_path or Config.MODEL_PATH
        self.cascade_path = cascade_path or Config.CASCADE_PATH
        self.classes_path = Config.CLASSES_PATH
        self.uploads_dir = Config.UPLOAD_FOLDER

        # 1. Load Class Mapping
        if os.path.exists(self.classes_path):
            with open(self.classes_path, "r") as f:
                self.classes = json.load(f)
        else:
            self.classes = ["fake", "real"]

        # 2. Initialize ResNet-18 Model without re-downloading ImageNet weights
        self.model = DeepfakeDetectorNet(num_classes=len(self.classes), pretrained=False).to(self.device)
        if os.path.exists(self.model_path):
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        # 3. Initialize Face Detector
        if not os.path.exists(self.cascade_path):
            raise FileNotFoundError(f"Haar Cascade not found at: {self.cascade_path}")
        self.face_cascade = cv2.CascadeClassifier(self.cascade_path)

        # 4. Image Preprocessing Transformation (ImageNet standard)
        self.transform = transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        os.makedirs(self.uploads_dir, exist_ok=True)

    def detect_and_crop_face(self, image_bgr, padding_ratio=0.15):
        """
        Intelligently detects human faces using multi-pass cascade detection.
        Robust to indoor lighting, slight head tilts, and mobile camera compression.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        h_img, w_img, _ = image_bgr.shape
        annotated_bgr = image_bgr.copy()

        # Pass 1: Standard detection
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )

        # Pass 2: Contrast-enhanced fallback (for dark photos or shadowed faces)
        if len(faces) == 0:
            equalized_gray = cv2.equalizeHist(gray)
            faces = self.face_cascade.detectMultiScale(
                equalized_gray,
                scaleFactor=1.08,
                minNeighbors=4,
                minSize=(40, 40)
            )

        # Pass 3: Sensitive fallback (for smaller faces or tilted angles)
        if len(faces) == 0:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(35, 35)
            )

        if len(faces) == 0:
            side = int(min(h_img, w_img) * 0.75)
            start_x = (w_img - side) // 2
            start_y = max(0, int((h_img - side) * 0.40))
            crop_bgr = image_bgr[start_y:start_y + side, start_x:start_x + side]
            cv2.rectangle(annotated_bgr, (start_x, start_y), (start_x + side, start_y + side), (255, 165, 0), 2)
            cv2.putText(annotated_bgr, "Est. Facial Region", (start_x, max(22, start_y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 165, 0), 2)
            return crop_bgr, annotated_bgr, False, [start_x, start_y, side, side], 0

        # Sort faces by area descending (primary subject first)
        faces = sorted(faces, key=lambda f: int(f[2]) * int(f[3]), reverse=True)
        primary_area = int(faces[0][2]) * int(faces[0][3])

        valid_faces = [f for f in faces if (int(f[2]) * int(f[3])) >= (primary_area * 0.25)]

        for idx, (fx, fy, fw, fh) in enumerate(valid_faces):
            color = (0, 255, 0) if idx == 0 else (255, 180, 0)
            label = "Primary Face" if idx == 0 else f"Face #{idx+1}"
            cv2.rectangle(annotated_bgr, (int(fx), int(fy)), (int(fx + fw), int(fy + fh)), color, 2)
            cv2.putText(annotated_bgr, label, (int(fx), max(22, int(fy) - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        x, y, w, h = valid_faces[0]
        pad_w = int(w * padding_ratio)
        pad_h = int(h * padding_ratio)

        x1 = max(0, int(x) - pad_w)
        y1 = max(0, int(y) - pad_h)
        x2 = min(w_img, int(x + w) + pad_w)
        y2 = min(h_img, int(y + h) + pad_h)

        crop_bgr = image_bgr[y1:y2, x1:x2]
        native_bbox = [int(x), int(y), int(w), int(h)]
        return crop_bgr, annotated_bgr, True, native_bbox, len(valid_faces)

    def predict(self, image_path, mode="standard", save_artifacts=True, artifact_prefix=""):
        """
        Hybrid Forensic Prediction:
        Fuses ResNet-18 Deep Representations + Multi-Domain Forensic Signals (Sensor + FFT + ELA + Chromatic)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError("Unable to read image. Please provide a valid JPG or PNG.")

        with open(image_path, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        cropped_face, annotated_img, face_found, bbox, face_count = self.detect_and_crop_face(img_bgr)

        face_rgb = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
        pil_face = Image.fromarray(face_rgb)
        tensor_face = self.transform(pil_face).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor_face)
            neural_probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        neural_fake = float(neural_probs[0])
        neural_real = float(neural_probs[1])

        forensics = extract_forensic_signals(cropped_face, mode=mode)

        combined_real_prob = (
            0.25 * neural_real +
            0.25 * forensics["sensor_real_score"] +
            0.25 * forensics["fft_real_score"] +
            0.15 * forensics["ela_real_score"] +
            0.10 * forensics["chroma_real_score"]
        ) * 100.0

        if mode == "portrait" and forensics["fft_real_score"] >= 0.75 and forensics["ela_real_score"] >= 0.75:
            combined_real_prob = min(96.5, combined_real_prob + 8.0)

        combined_real_prob = float(np.clip(combined_real_prob, 5.0, 97.5))
        combined_fake_prob = float(100.0 - combined_real_prob)

        if combined_real_prob >= 50.0:
            prediction = "REAL"
            confidence = combined_real_prob
        else:
            prediction = "FAKE"
            confidence = combined_fake_prob

        base_name = os.path.basename(image_path)
        stem = os.path.splitext(base_name)[0]
        prefix = f"{artifact_prefix}_" if artifact_prefix else ""
        
        face_filename = f"face_{prefix}{stem}.jpg"
        annotated_filename = f"annotated_{prefix}{stem}.jpg"
        ela_filename = f"ela_{prefix}{stem}.jpg"
        fft_filename = f"fft_{prefix}{stem}.jpg"

        face_save_path = os.path.join(self.uploads_dir, face_filename)
        annotated_save_path = os.path.join(self.uploads_dir, annotated_filename)
        ela_save_path = os.path.join(self.uploads_dir, ela_filename)
        fft_save_path = os.path.join(self.uploads_dir, fft_filename)

        if save_artifacts:
            cv2.imwrite(face_save_path, cropped_face)
            cv2.imwrite(annotated_save_path, annotated_img)
            cv2.imwrite(ela_save_path, forensics["ela_heatmap"])
            cv2.imwrite(fft_save_path, forensics["fft_heatmap"])

        if face_found:
            status_desc = f"Localized {face_count} face(s). {forensics['sensor_status']}; {forensics['fft_status']}."
        else:
            status_desc = f"Central facial ROI evaluated. {forensics['sensor_status']}."

        return {
            "prediction": str(prediction),
            "confidence": round(float(confidence), 2),
            "real_probability": round(float(combined_real_prob), 2),
            "fake_probability": round(float(combined_fake_prob), 2),
            "face_detected": bool(face_found),
            "face_count": int(face_count),
            "bounding_box": [int(v) for v in bbox] if bbox else None,
            "analysis_status": str(status_desc),
            "mode": mode,
            "sha256": sha256_hash,
            "face_image_path": f"static/uploads/{face_filename}",
            "annotated_image_path": f"static/uploads/{annotated_filename}",
            "ela_image_path": f"static/uploads/{ela_filename}",
            "fft_image_path": f"static/uploads/{fft_filename}",
            "forensics": {
                "sensor_noise_variance": forensics["lap_var"],
                "sensor_check": forensics["sensor_check"],
                "frequency_fft_ratio": forensics["fft_ratio"],
                "fft_check": forensics["fft_check"],
                "ela_mean": forensics["ela_mean"],
                "ela_check": forensics["ela_check"],
                "chromatic_coherence": forensics["chroma"],
                "chroma_check": forensics["chroma_check"]
            }
        }

    def predict_multi_face(self, image_path, mode="standard", save_artifacts=True, artifact_prefix=""):
        """
        Multiple Face Detection & Independent CNN Verification:
        Detects all faces in image, crops each, evaluates model & forensics separately,
        and annotates distinct bounding boxes (REAL = Green, FAKE = Red).
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError("Unable to read image. Please provide a valid JPG or PNG.")

        with open(image_path, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        h_img, w_img, _ = img_bgr.shape
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Multi-scale face detection tuned for group/crowd scenes
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(35, 35)
        )

        if len(faces) == 0:
            equalized_gray = cv2.equalizeHist(gray)
            faces = self.face_cascade.detectMultiScale(
                equalized_gray,
                scaleFactor=1.08,
                minNeighbors=3,
                minSize=(30, 30)
            )

        if len(faces) == 0:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=2,
                minSize=(25, 25)
            )

        base_name = os.path.basename(image_path)
        stem = os.path.splitext(base_name)[0]
        prefix = f"{artifact_prefix}_" if artifact_prefix else ""
        annotated_multi_filename = f"annotated_multi_{prefix}{stem}.jpg"
        annotated_multi_path = os.path.join(self.uploads_dir, annotated_multi_filename)

        if len(faces) == 0:
            annotated_img = img_bgr.copy()
            cv2.putText(annotated_img, "No Human Faces Detected", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            if save_artifacts:
                cv2.imwrite(annotated_multi_path, annotated_img)

            return {
                "face_count": 0,
                "faces": [],
                "overall_prediction": "UNKNOWN",
                "overall_confidence": 0.0,
                "real_count": 0,
                "fake_count": 0,
                "annotated_image_path": f"static/uploads/{annotated_multi_filename}",
                "sha256": sha256_hash,
                "analysis_status": "No human faces detected in the uploaded image. Please ensure faces are well-lit and unobstructed.",
                "mode": mode
            }

        # Filter overlapping / duplicate detections
        valid_faces = []
        for f in faces:
            fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
            overlap = False
            for vx, vy, vw, vh in valid_faces:
                if abs((fx + fw // 2) - (vx + vw // 2)) < 25 and abs((fy + fh // 2) - (vy + vh // 2)) < 25:
                    overlap = True
                    break
            if not overlap:
                valid_faces.append((fx, fy, fw, fh))

        # Sort spatially left-to-right
        valid_faces = sorted(valid_faces, key=lambda f: f[0])

        annotated_img = img_bgr.copy()
        face_results = []
        real_count = 0
        fake_count = 0
        highest_fake_conf = 0.0
        sum_conf = 0.0

        for idx, (x, y, w, h) in enumerate(valid_faces):
            face_index = idx + 1
            pad_w = int(w * 0.15)
            pad_h = int(h * 0.15)
            x1 = max(0, x - pad_w)
            y1 = max(0, y - pad_h)
            x2 = min(w_img, x + w + pad_w)
            y2 = min(h_img, y + h + pad_h)
            crop_bgr = img_bgr[y1:y2, x1:x2]

            face_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil_face = Image.fromarray(face_rgb)
            tensor_face = self.transform(pil_face).unsqueeze(0).to(self.device)

            with torch.no_grad():
                logits = self.model(tensor_face)
                neural_probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

            neural_fake = float(neural_probs[0])
            neural_real = float(neural_probs[1])

            forensics = extract_forensic_signals(crop_bgr, mode=mode)

            combined_real_prob = (
                0.25 * neural_real +
                0.25 * forensics["sensor_real_score"] +
                0.25 * forensics["fft_real_score"] +
                0.15 * forensics["ela_real_score"] +
                0.10 * forensics["chroma_real_score"]
            ) * 100.0

            if mode == "portrait" and forensics["fft_real_score"] >= 0.75 and forensics["ela_real_score"] >= 0.75:
                combined_real_prob = min(96.5, combined_real_prob + 8.0)

            combined_real_prob = float(np.clip(combined_real_prob, 5.0, 97.5))
            combined_fake_prob = float(100.0 - combined_real_prob)

            if combined_real_prob >= 50.0:
                face_pred = "REAL"
                face_conf = combined_real_prob
                real_count += 1
                box_color = (0, 200, 0)      # Green for Authentic
            else:
                face_pred = "FAKE"
                face_conf = combined_fake_prob
                fake_count += 1
                highest_fake_conf = max(highest_fake_conf, face_conf)
                box_color = (0, 0, 220)      # Red for Deepfake

            sum_conf += face_conf

            # Master Composite Annotation with solid badge pill
            cv2.rectangle(annotated_img, (x, y), (x + w, y + h), box_color, 2)
            badge_label = f"#{face_index} {face_pred} {round(face_conf)}%"
            (tw, th), _ = cv2.getTextSize(badge_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated_img, (x, max(0, y - th - 8)), (x + tw + 8, y), box_color, -1)
            cv2.putText(annotated_img, badge_label, (x + 4, max(th + 2, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            face_crop_filename = f"crop_{prefix}{stem}_face{face_index}.jpg"
            face_crop_path = os.path.join(self.uploads_dir, face_crop_filename)
            if save_artifacts:
                cv2.imwrite(face_crop_path, crop_bgr)

            face_results.append({
                "face_index": face_index,
                "bounding_box": [x, y, w, h],
                "prediction": face_pred,
                "confidence": round(float(face_conf), 1),
                "real_probability": round(float(combined_real_prob), 1),
                "fake_probability": round(float(combined_fake_prob), 1),
                "crop_path": f"static/uploads/{face_crop_filename}",
                "forensics": {
                    "sensor_noise_variance": forensics["lap_var"],
                    "sensor_check": forensics["sensor_check"],
                    "frequency_fft_ratio": forensics["fft_ratio"],
                    "fft_check": forensics["fft_check"],
                    "ela_mean": forensics["ela_mean"],
                    "ela_check": forensics["ela_check"],
                    "chromatic_coherence": forensics["chroma"],
                    "chroma_check": forensics["chroma_check"]
                }
            })

        if save_artifacts:
            cv2.imwrite(annotated_multi_path, annotated_img)

        if fake_count > 0:
            overall_pred = "FAKE"
            overall_conf = highest_fake_conf
            status_summary = f"Detected {len(valid_faces)} face(s): {fake_count} manipulated face(s) identified."
        else:
            overall_pred = "REAL"
            overall_conf = sum_conf / len(valid_faces)
            status_summary = f"Detected {len(valid_faces)} face(s): All faces verified authentic."

        return {
            "face_count": len(valid_faces),
            "faces": face_results,
            "overall_prediction": overall_pred,
            "overall_confidence": round(float(overall_conf), 1),
            "real_count": real_count,
            "fake_count": fake_count,
            "annotated_image_path": f"static/uploads/{annotated_multi_filename}",
            "sha256": sha256_hash,
            "analysis_status": status_summary,
            "mode": mode
        }

# Lazy Singleton Instance Provider
_predictor_instance = None

def get_predictor():
    """Returns the singleton instance of DeepfakePredictor (lazy-loaded)"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = DeepfakePredictor()
    return _predictor_instance
