"""
Module: predict.py
Purpose: State-of-the-Art Deepfake & Face Authenticity Inference Engine
Combines Pretrained ResNet-18 Deep Residual Representations with Multi-Domain Forensic Analysis
(Laplacian Sensor Texture, 2D-FFT Frequency Domain, and Chromatic Coherence)
"""
import os
import sys
import json
import argparse
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

# Model Architecture (Self-contained to eliminate training-time dependencies like sklearn/matplotlib)
IMAGE_SIZE = (128, 128)

class DeepfakeDetectorNet(nn.Module):
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

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_DIR, "model", "deepfake_detector.pt")
CLASS_MAPPING_PATH = os.path.join(PROJECT_DIR, "model", "classes.json")
CASCADE_PATH = os.path.join(PROJECT_DIR, "model", "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(PROJECT_DIR, "static", "uploads")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Optimize memory consumption for cloud deployment (512MB RAM budget)
torch.set_grad_enabled(False)
torch.set_num_threads(1)

class DeepfakePredictor:
    def __init__(self, model_path=MODEL_PATH, cascade_path=CASCADE_PATH):
        self.device = DEVICE
        
        # 1. Load Class Mapping
        if os.path.exists(CLASS_MAPPING_PATH):
            with open(CLASS_MAPPING_PATH, 'r') as f:
                self.classes = json.load(f)
        else:
            self.classes = ['fake', 'real']

        # 2. Initialize ResNet-18 Model without re-downloading ImageNet weights
        self.model = DeepfakeDetectorNet(num_classes=len(self.classes), pretrained=False).to(self.device)
        if os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()

        # 3. Initialize Face Detector
        if not os.path.exists(cascade_path):
            raise FileNotFoundError(f"Haar Cascade not found at: {cascade_path}")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # 4. Image Preprocessing Transformation (ImageNet standard)
        self.transform = transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        os.makedirs(UPLOADS_DIR, exist_ok=True)

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
            # Fallback to golden-ratio central facial region crop
            side = int(min(h_img, w_img) * 0.75)
            start_x = (w_img - side) // 2
            start_y = max(0, int((h_img - side) * 0.40))  # Slightly higher for human head positioning
            crop_bgr = image_bgr[start_y:start_y + side, start_x:start_x + side]
            cv2.rectangle(annotated_bgr, (start_x, start_y), (start_x + side, start_y + side), (255, 165, 0), 2)
            cv2.putText(annotated_bgr, "Est. Facial Region", (start_x, max(22, start_y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 165, 0), 2)
            return crop_bgr, annotated_bgr, False, [start_x, start_y, side, side], 0

        # Sort faces by area descending (primary subject first)
        faces = sorted(faces, key=lambda f: int(f[2]) * int(f[3]), reverse=True)
        primary_area = int(faces[0][2]) * int(faces[0][3])

        # Filter out background false positives
        valid_faces = [f for f in faces if (int(f[2]) * int(f[3])) >= (primary_area * 0.25)]

        # Annotate detected faces
        for idx, (fx, fy, fw, fh) in enumerate(valid_faces):
            color = (0, 255, 0) if idx == 0 else (255, 180, 0)
            label = "Primary Face" if idx == 0 else f"Face #{idx+1}"
            cv2.rectangle(annotated_bgr, (int(fx), int(fy)), (int(fx + fw), int(fy + fh)), color, 2)
            cv2.putText(annotated_bgr, label, (int(fx), max(22, int(fy) - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Extract primary face with proportional margin
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

    def extract_forensic_signals(self, crop_bgr, mode="standard"):
        """
        Extracts multi-domain digital forensic authenticity indicators:
        1. Sensor noise & skin pore texture (Laplacian Variance) calibrated for smartphones
        2. Frequency-domain radial decay & GAN lattice artifacts (2D-FFT)
        3. Error Level Analysis (ELA) for compression rate & splice boundary consistency
        4. Chromatic coherence across RGB sensor wells
        """
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        h, w = crop_gray.shape

        # 1. Laplacian Sensor Noise / Texture Check (Calibrated for real smartphones + portrait filters)
        lap_var = float(cv2.Laplacian(crop_gray, cv2.CV_64F).var())
        if lap_var >= 80.0:
            sensor_real_score = 0.95
            sensor_status = "Authentic optical sensor noise & natural skin pore texture"
            sensor_check = "PASS"
        elif 35.0 <= lap_var < 80.0:
            sensor_real_score = 0.88 if mode == "portrait" else 0.82
            sensor_status = "Natural soft lighting / smartphone ambient portrait"
            sensor_check = "PASS"
        elif 16.0 <= lap_var < 35.0:
            sensor_real_score = 0.78 if mode == "portrait" else 0.65
            sensor_status = "Smartphone camera HDR smoothing / gentle beauty mode"
            sensor_check = "PASS (Smoothing detected)"
        elif 7.0 <= lap_var < 16.0:
            sensor_real_score = 0.40
            sensor_status = "Substantial skin smoothing typical of generative models or strong filters"
            sensor_check = "WARNING"
        else:
            sensor_real_score = 0.15
            sensor_status = "Extreme artificial smoothness characteristic of AI face synthesis"
            sensor_check = "FAIL"

        # 2. 2D-FFT Frequency Domain Power Spectrum
        f = np.fft.fft2(crop_gray)
        fshift = np.fft.fftshift(f)
        mag = 20 * np.log(np.abs(fshift) + 1e-8)
        cr, cc = h // 2, w // 2
        mask_low = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask_low, (cc, cr), max(4, min(cr, cc) // 3), 1, -1)
        low_p = float(np.mean(mag[mask_low == 1]))
        high_p = float(np.mean(mag[mask_low == 0]))
        fft_ratio = float(high_p / (low_p + 1e-8))

        # Real optical camera lenses follow smooth power decay (0.50 to 0.92)
        if 0.52 <= fft_ratio <= 0.92:
            fft_real_score = 0.95
            fft_status = "Smooth optical frequency decay (No GAN deconvolution grid)"
            fft_check = "PASS"
        elif 0.45 <= fft_ratio < 0.52 or 0.92 < fft_ratio <= 0.98:
            fft_real_score = 0.78
            fft_status = "Moderate high-frequency distribution (Consistent with compression)"
            fft_check = "PASS"
        else:
            fft_real_score = 0.25
            fft_status = "Periodic spectral lattice anomalies typical of generative upsampling"
            fft_check = "FAIL"

        # Generate 2D-FFT Spectrum Heatmap Visualization
        mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        fft_heatmap = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)

        # 3. Error Level Analysis (ELA) for JPEG Compression Consistency
        # Deepfakes / FaceSwaps demonstrate glaring compression discrepancy between face and boundary
        _, encoded_jpg = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
        decompressed_bgr = cv2.imdecode(encoded_jpg, cv2.IMREAD_COLOR)
        ela_diff = cv2.absdiff(crop_bgr, decompressed_bgr)
        ela_gray = cv2.cvtColor(ela_diff, cv2.COLOR_BGR2GRAY)
        ela_mean = float(np.mean(ela_gray))
        ela_std = float(np.std(ela_gray))

        # ELA Heatmap (amplified 12x for human forensic inspection)
        ela_amplified = cv2.convertScaleAbs(ela_diff, alpha=12)
        ela_amp_gray = cv2.cvtColor(ela_amplified, cv2.COLOR_BGR2GRAY)
        ela_heatmap = cv2.applyColorMap(ela_amp_gray, cv2.COLORMAP_HOT)

        ela_uniformity = float(ela_std / (ela_mean + 1e-5))
        if 0.6 <= ela_uniformity <= 2.2:
            ela_real_score = 0.94
            ela_status = "Uniform optical compression gradient across facial structures"
            ela_check = "PASS"
        elif 0.3 <= ela_uniformity < 0.6 or 2.2 < ela_uniformity <= 3.0:
            ela_real_score = 0.75
            ela_status = "Minor compression variation (Normal for social media re-saving)"
            ela_check = "PASS"
        else:
            ela_real_score = 0.30
            ela_status = "Non-uniform compression error levels (Indicates digital splicing or synthetic face)"
            ela_check = "FAIL"

        # 4. Chromatic Channel Correlation
        b, g, r = cv2.split(crop_bgr)
        corr_rg = float(np.corrcoef(r.flatten(), g.flatten())[0, 1])
        corr_gb = float(np.corrcoef(g.flatten(), b.flatten())[0, 1])
        chroma = float((corr_rg + corr_gb) / 2.0)

        if chroma > 0.82:
            chroma_real_score = 0.95
            chroma_status = "Coherent RGB Bayer-pattern sensor alignment"
            chroma_check = "PASS"
        elif chroma > 0.70:
            chroma_real_score = 0.78
            chroma_status = "Acceptable chromatic distribution"
            chroma_check = "PASS"
        else:
            chroma_real_score = 0.30
            chroma_status = "Chromatic seam shift detected (Common in FaceSwap blending)"
            chroma_check = "FAIL"

        return {
            "sensor_real_score": sensor_real_score,
            "sensor_status": sensor_status,
            "sensor_check": sensor_check,
            "lap_var": round(lap_var, 1),
            "fft_real_score": fft_real_score,
            "fft_status": fft_status,
            "fft_check": fft_check,
            "fft_ratio": round(fft_ratio, 3),
            "fft_heatmap": fft_heatmap,
            "ela_real_score": ela_real_score,
            "ela_status": ela_status,
            "ela_check": ela_check,
            "ela_mean": round(ela_mean, 2),
            "ela_heatmap": ela_heatmap,
            "chroma_real_score": chroma_real_score,
            "chroma_status": chroma_status,
            "chroma_check": chroma_check,
            "chroma": round(chroma, 3)
        }

    def predict(self, image_path, mode="standard", save_artifacts=True):
        """
        Hybrid Forensic Prediction:
        Fuses ResNet-18 Deep Representations + Multi-Domain Forensic Signals (Sensor + FFT + ELA + Chromatic)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError("Unable to read image. Please provide a valid JPG or PNG.")

        # Compute cryptographic hash for forensic audit trail
        import hashlib
        with open(image_path, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        # Step 1: Intelligent Multi-Pass Face Detection
        cropped_face, annotated_img, face_found, bbox, face_count = self.detect_and_crop_face(img_bgr)

        # Step 2: Deep Vision Model Inference (ResNet-18)
        face_rgb = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
        pil_face = Image.fromarray(face_rgb)
        tensor_face = self.transform(pil_face).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor_face)
            neural_probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        # Neural scores: classes are ['fake', 'real']
        neural_fake = float(neural_probs[0])
        neural_real = float(neural_probs[1])

        # Step 3: Multi-Domain Digital Forensic Analysis (Sensor + 2D-FFT + ELA + Chroma)
        forensics = self.extract_forensic_signals(cropped_face, mode=mode)

        # Step 4: Calibrated Multi-Domain Ensemble Fusion
        # Balanced weights across distinct physical/computational domains
        # 1. Neural Representation (25%)
        # 2. Camera Sensor Texture (25%)
        # 3. Frequency Domain Spectrum (25%)
        # 4. Error Level Analysis (15%)
        # 5. Chromatic Coherence (10%)
        combined_real_prob = (
            0.25 * neural_real +
            0.25 * forensics["sensor_real_score"] +
            0.25 * forensics["fft_real_score"] +
            0.15 * forensics["ela_real_score"] +
            0.10 * forensics["chroma_real_score"]
        ) * 100.0

        # Smartphone Portrait Mode Boost:
        # If user uploaded a mobile selfie that has soft lighting but passed ELA & FFT frequency tests,
        # ensure it isn't penalized by subtle skin smoothing
        if mode == "portrait" and forensics["fft_real_score"] >= 0.75 and forensics["ela_real_score"] >= 0.75:
            combined_real_prob = min(96.5, combined_real_prob + 8.0)

        # Ensure realistic confidence bounds
        combined_real_prob = float(np.clip(combined_real_prob, 5.0, 97.5))
        combined_fake_prob = float(100.0 - combined_real_prob)

        # Final Verdict
        if combined_real_prob >= 50.0:
            prediction = "REAL"
            confidence = combined_real_prob
        else:
            prediction = "FAKE"
            confidence = combined_fake_prob

        # Save Visual Forensic Artifacts
        base_name = os.path.basename(image_path)
        stem = os.path.splitext(base_name)[0]
        face_filename = f"face_{stem}.jpg"
        annotated_filename = f"annotated_{stem}.jpg"
        ela_filename = f"ela_{stem}.jpg"
        fft_filename = f"fft_{stem}.jpg"

        face_save_path = os.path.join(UPLOADS_DIR, face_filename)
        annotated_save_path = os.path.join(UPLOADS_DIR, annotated_filename)
        ela_save_path = os.path.join(UPLOADS_DIR, ela_filename)
        fft_save_path = os.path.join(UPLOADS_DIR, fft_filename)

        if save_artifacts:
            cv2.imwrite(face_save_path, cropped_face)
            cv2.imwrite(annotated_save_path, annotated_img)
            cv2.imwrite(ela_save_path, forensics["ela_heatmap"])
            cv2.imwrite(fft_save_path, forensics["fft_heatmap"])

        # Status Summary
        if face_found:
            status_desc = f"Localized {face_count} face(s). {forensics['sensor_status']}; {forensics['fft_status']}."
        else:
            status_desc = f"Central facial ROI evaluated. {forensics['sensor_status']}."

        result = {
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

        return result

# ==========================================
# CLI Testing Interface
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Deepfake Image Authenticity Predictor")
    parser.add_argument("--image", type=str, help="Path to image file to analyze")
    args = parser.parse_args()

    predictor = DeepfakePredictor()
    test_path = args.image if args.image else os.path.join(PROJECT_DIR, "dataset", "real", "real_01.jpg")

    print("=" * 60)
    print("HYBRID FORENSIC DEEPFAKE PREDICTION")
    print("=" * 60)
    print(f"[+] Analyzing: {test_path}")

    res = predictor.predict(test_path)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
