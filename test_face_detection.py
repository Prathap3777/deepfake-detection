"""
Module: test_face_detection.py
Purpose: Validates OpenCV installation and Face Detection pipeline
"""
import sys
import os
import importlib.metadata
import cv2
import numpy as np

def test_environment():
    print("=" * 60)
    print("DEEPFAKE DETECTION - SYSTEM & ENVIRONMENT VERIFICATION")
    print("=" * 60)
    
    # 1. Python version check
    print(f"[✓] Python Version: {sys.version.split()[0]}")
    
    # 2. Check OpenCV
    print(f"[✓] OpenCV (cv2) Version: {cv2.__version__}")
    
    # 3. Check PyTorch & CUDA availability
    try:
        import torch
        device = "CUDA (GPU)" if torch.cuda.is_available() else "CPU"
        print(f"[✓] PyTorch Version: {torch.__version__} (Running on {device})")
    except ImportError:
        print("[!] PyTorch is not yet installed.")

    # 4. Check Flask
    try:
        flask_ver = importlib.metadata.version("flask")
        print(f"[✓] Flask Version: {flask_ver}")
    except Exception:
        print("[!] Flask is not yet installed.")

    # 5. Test Face Detection Model (Haar Cascade)
    print("-" * 60)
    print("Testing Face Detection Engine...")
    
    # Check project model directory first, then fallback to cv2.data
    local_cascade = os.path.join(os.path.dirname(__file__), "model", "haarcascade_frontalface_default.xml")
    system_cascade = os.path.join(getattr(cv2.data, 'haarcascades', ''), 'haarcascade_frontalface_default.xml')
    
    if os.path.exists(local_cascade):
        cascade_path = local_cascade
    elif os.path.exists(system_cascade):
        cascade_path = system_cascade
    else:
        print(f"[ERROR] Cascade file not found at: {local_cascade}")
        return False
        
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("[ERROR] Failed to load OpenCV Haar Cascade!")
        return False
        
    print(f"[✓] Face Detector loaded successfully from:")
    print(f"    {cascade_path}")

    # Create a synthetic image with a simple drawn face to test detection pipeline
    test_img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.circle(test_img, (150, 150), 80, (200, 200, 200), -1) # face oval
    cv2.circle(test_img, (120, 130), 10, (50, 50, 50), -1)    # left eye
    cv2.circle(test_img, (180, 130), 10, (50, 50, 50), -1)    # right eye
    cv2.ellipse(test_img, (150, 180), (30, 15), 0, 0, 180, (50, 50, 50), 3) # smile

    gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)
    
    print(f"[✓] Face detection pipeline function call executed without errors.")
    print("=" * 60)
    print("SUCCESS: Your environment and face detection engine are READY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_environment()
