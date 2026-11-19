"""
Module: prepare_dataset.py
Purpose: Prepares, validates, face-crops, and splits dataset into Train/Val/Test
"""
import os
import sys
import glob
import random
import urllib.request
import cv2
import numpy as np
from PIL import Image

# Configuration Constants
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset")
RAW_REAL_DIR = os.path.join(DATASET_DIR, "real")
RAW_FAKE_DIR = os.path.join(DATASET_DIR, "fake")
PROCESSED_DIR = os.path.join(DATASET_DIR, "processed")
CASCADE_PATH = os.path.join(PROJECT_DIR, "model", "haarcascade_frontalface_default.xml")
TARGET_SIZE = (128, 128)
RANDOM_SEED = 42

# Publicly available sample faces for instant bootstrapping (OpenCV & Public Domain)
SAMPLE_REAL_URLS = [
    ("https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg", "real_01.jpg"),
    ("https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=500&q=80", "real_02.jpg"),
    ("https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&q=80", "real_03.jpg"),
    ("https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=80", "real_04.jpg"),
    ("https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=500&q=80", "real_05.jpg"),
    ("https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80", "real_06.jpg"),
    ("https://images.unsplash.com/photo-1517841905240-472988babdf9?w=500&q=80", "real_07.jpg"),
    ("https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=500&q=80", "real_08.jpg"),
    ("https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=500&q=80", "real_09.jpg"),
    ("https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=500&q=80", "real_10.jpg"),
]

def load_face_detector():
    """Loads OpenCV Haar Cascade Face Detector"""
    if not os.path.exists(CASCADE_PATH):
        raise FileNotFoundError(f"Cascade not found at: {CASCADE_PATH}")
    detector = cv2.CascadeClassifier(CASCADE_PATH)
    if detector.empty():
        raise RuntimeError("Failed to initialize CascadeClassifier")
    return detector

def extract_face(img_path, detector, padding_ratio=0.15):
    """
    Detects face, adds contextual margin, crops, and resizes.
    Returns (cropped_bgr_img, success_bool)
    """
    img = cv2.imread(img_path)
    if img is None:
        return None, False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

    if len(faces) == 0:
        # If no face detected via cascade, take center crop as fallback
        h, w, _ = img.shape
        side = min(h, w)
        start_x = (w - side) // 2
        start_y = (h - side) // 2
        crop = img[start_y:start_y + side, start_x:start_x + side]
        resized = cv2.resize(crop, TARGET_SIZE)
        return resized, True

    # Pick the largest face detected
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = faces[0]

    # Add margin around face to preserve jawline, hairline, and manipulation boundaries
    pad_w = int(w * padding_ratio)
    pad_h = int(h * padding_ratio)
    img_h, img_w, _ = img.shape

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(img_w, x + w + pad_w)
    y2 = min(img_h, y + h + pad_h)

    face_crop = img[y1:y2, x1:x2]
    resized = cv2.resize(face_crop, TARGET_SIZE)
    return resized, True

def generate_deepfake_artifacts(real_face_bgr):
    """
    Creates realistic deepfake manipulation patterns (frequency noise,
    boundary blurring, color misalignment, warp artefacts) from a real face.
    This simulates StyleGAN/FaceSwap digital signatures.
    """
    fake = real_face_bgr.copy()
    h, w, _ = fake.shape

    # 1. Color domain alteration (slight channel hue mismatch common in swapped faces)
    hsv = cv2.cvtColor(fake, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + random.uniform(3, 8)) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * random.uniform(0.9, 1.15), 0, 255)
    fake = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 2. Localized boundary smoothing (simulating boundary blending seams)
    center = (w // 2, h // 2)
    radius = int(min(w, h) * 0.35)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)
    blurred = cv2.GaussianBlur(fake, (11, 11), 3.0)
    fake = np.where(mask[:, :, None] == 255, fake, cv2.addWeighted(fake, 0.4, blurred, 0.6, 0))

    # 3. High-frequency digital noise artefact (GAN checkerboard artifact simulation)
    noise = np.random.normal(0, random.uniform(4, 9), (h, w, 3)).astype(np.float32)
    fake = np.clip(fake.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 4. Subtle bilateral smoothing of skin texture (overly smooth deepfake skin)
    fake = cv2.bilateralFilter(fake, d=7, sigmaColor=40, sigmaSpace=40)

    return fake

def download_starter_samples():
    """Downloads sample face images if raw directories are empty"""
    os.makedirs(RAW_REAL_DIR, exist_ok=True)
    os.makedirs(RAW_FAKE_DIR, exist_ok=True)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print("[*] Checking sample images...")

    existing_real = [f for f in os.listdir(RAW_REAL_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if len(existing_real) < 5:
        print("[*] Downloading curated starter real faces for immediate testing...")
        for i, (url, fname) in enumerate(SAMPLE_REAL_URLS):
            target_file = os.path.join(RAW_REAL_DIR, fname)
            if not os.path.exists(target_file):
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response, open(target_file, 'wb') as out_file:
                        out_file.write(response.read())
                    print(f"    [+] Downloaded: {fname}")
                except Exception as e:
                    # If network block occurs, generate a high-quality procedural face pattern
                    print(f"    [-] Could not fetch {fname} ({e}), generating local procedural sample...")
                    procedural = np.full((300, 300, 3), (180 + i * 5, 200 - i * 3, 210), dtype=np.uint8)
                    cv2.circle(procedural, (150, 150), 90, (140, 160, 220), -1)
                    cv2.circle(procedural, (120, 130), 10, (40, 40, 40), -1)
                    cv2.circle(procedural, (180, 130), 10, (40, 40, 40), -1)
                    cv2.ellipse(procedural, (150, 185), (35, 18), 0, 0, 180, (40, 40, 150), 3)
                    cv2.imwrite(target_file, procedural)

    # Automatically generate corresponding Deepfake counterpart images if fake directory is empty
    existing_fake = [f for f in os.listdir(RAW_FAKE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if len(existing_fake) < 5:
        print("[*] Synthesizing realistic deepfake manipulated face samples...")
        real_images = glob.glob(os.path.join(RAW_REAL_DIR, "*.*"))
        for idx, r_img_path in enumerate(real_images):
            bgr = cv2.imread(r_img_path)
            if bgr is not None:
                # Generate two different manipulated variations for robust training
                fake_a = generate_deepfake_artifacts(bgr)
                fake_b = generate_deepfake_artifacts(fake_a)
                cv2.imwrite(os.path.join(RAW_FAKE_DIR, f"fake_sample_{idx}_a.jpg"), fake_a)
                cv2.imwrite(os.path.join(RAW_FAKE_DIR, f"fake_sample_{idx}_b.jpg"), fake_b)
        print(f"    [+] Generated deepfake manipulated counterparts in: {RAW_FAKE_DIR}")

def process_and_split_dataset(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15):
    """
    Processes all real and fake images:
    - Crops facial bounding boxes
    - Normalizes to (128, 128)
    - Partitions into Train / Val / Test sets
    """
    random.seed(RANDOM_SEED)
    detector = load_face_detector()

    # Destination directories
    splits = ["train", "val", "test"]
    classes = ["real", "fake"]
    for s in splits:
        for c in classes:
            os.makedirs(os.path.join(PROCESSED_DIR, s, c), exist_ok=True)

    def process_class(source_dir, class_name):
        extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(source_dir, ext)))
            files.extend(glob.glob(os.path.join(source_dir, ext.upper())))
        
        files = list(set(files))
        random.shuffle(files)

        n_total = len(files)
        if n_total == 0:
            print(f"[!] Warning: No images found in {source_dir}")
            return 0, 0, 0

        n_train = max(1, int(n_total * train_ratio))
        n_val = max(1, int(n_total * val_ratio))
        # remainder goes to test
        train_files = files[:n_train]
        val_files = files[n_train:n_train + n_val]
        test_files = files[n_train + n_val:]
        if len(test_files) == 0:
            test_files = val_files  # ensure non-empty test set for small datasets

        split_dict = {"train": train_files, "val": val_files, "test": test_files}
        counts = {}

        for split_name, f_list in split_dict.items():
            saved = 0
            for idx, filepath in enumerate(f_list):
                cropped, ok = extract_face(filepath, detector)
                if ok and cropped is not None:
                    out_name = f"{class_name}_{split_name}_{idx:04d}.jpg"
                    out_path = os.path.join(PROCESSED_DIR, split_name, class_name, out_name)
                    cv2.imwrite(out_path, cropped)
                    saved += 1
            counts[split_name] = saved

        return counts["train"], counts["val"], counts["test"]

    print("=" * 60)
    print("PREPROCESSING & SPLITTING DATASET")
    print("=" * 60)
    print(f"[+] Scanning raw directories:")
    print(f"    Real: {RAW_REAL_DIR}")
    print(f"    Fake: {RAW_FAKE_DIR}")

    r_train, r_val, r_test = process_class(RAW_REAL_DIR, "real")
    f_train, f_val, f_test = process_class(RAW_FAKE_DIR, "fake")

    print("-" * 60)
    print(f"{'Split':<12} | {'Real Faces':<12} | {'Fake Faces':<12} | {'Total':<10}")
    print("-" * 60)
    print(f"{'Train (70%)':<12} | {r_train:<12} | {f_train:<12} | {r_train + f_train:<10}")
    print(f"{'Val (15%)':<12} | {r_val:<12} | {f_val:<12} | {r_val + f_val:<10}")
    print(f"{'Test (15%)':<12} | {r_test:<12} | {f_test:<12} | {r_test + f_test:<10}")
    print("=" * 60)
    print(f"[✓] Processed face crops saved to: {PROCESSED_DIR}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    download_starter_samples()
    process_and_split_dataset()
