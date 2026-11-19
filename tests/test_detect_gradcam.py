"""
FACEGUARD AI - Grad-CAM Explainable AI Test Suite
Module: tests/test_detect_gradcam.py
"""
import os
import io
import pytest
import numpy as np
import cv2
from faceguard import create_app
from faceguard.config import TestingConfig, BASE_DIR
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan, FaceResult
from faceguard.core.detector import DeepfakePredictor
from faceguard.core.gradcam import GradCAM

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_face_image(tmp_path):
    """Uses Lena dataset image or creates a realistic test face portrait"""
    dataset_img = os.path.join(BASE_DIR, "dataset", "real", "real_01.jpg")
    if os.path.exists(dataset_img):
        return dataset_img

    img = np.ones((200, 200, 3), dtype=np.uint8) * 180
    cv2.circle(img, (100, 100), 60, (200, 180, 160), -1)
    cv2.circle(img, (80, 85), 10, (50, 50, 50), -1)
    cv2.circle(img, (120, 85), 10, (50, 50, 50), -1)
    cv2.ellipse(img, (100, 125), (25, 12), 0, 0, 180, (40, 40, 200), 3)

    path = tmp_path / "gradcam_test.jpg"
    cv2.imwrite(str(path), img)
    return str(path)

def test_gradcam_requires_login(client):
    """Unauthenticated visitors are redirected to login"""
    response = client.get("/detect/gradcam")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_gradcam_page_renders_for_logged_in_user(app, client):
    """Authenticated users can access the Grad-CAM visualizer"""
    with app.app_context():
        user = User(full_name="Karen XAI", email="karen@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "karen@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/gradcam")
    assert res.status_code == 200
    assert b"Explainable AI (Grad-CAM) Visualizer" in res.data
    assert b"Generate Grad-CAM Heatmap" in res.data

def test_gradcam_rejects_empty_or_invalid_file(app, client):
    """Rejects empty submissions or unsupported file formats"""
    with app.app_context():
        user = User(full_name="Leo Tester", email="leo@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "leo@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty post
    res_empty = client.post("/detect/gradcam", data={}, follow_redirects=True)
    assert res_empty.status_code == 200
    assert b"Please choose a valid JPG or PNG image to generate a Grad-CAM" in res_empty.data

    # Invalid extension
    bad_data = {"image": (io.BytesIO(b"data"), "invalid.doc")}
    res_bad = client.post("/detect/gradcam", data=bad_data, follow_redirects=True)
    assert res_bad.status_code == 200
    assert b"Unsupported file type" in res_bad.data

def test_gradcam_generation_end_to_end(app, client, sample_face_image):
    """Tests end-to-end Grad-CAM generation, overlay rendering, and DB persistence"""
    with app.app_context():
        user = User(full_name="Mona Analyst", email="mona@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={"email": "mona@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(sample_face_image, "rb") as f:
        file_bytes = f.read()

    data = {"image": (io.BytesIO(file_bytes), "sample_portrait.jpg")}
    res = client.post("/detect/gradcam", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert res.status_code == 200
    assert b"Side-by-Side Visual Forensic Decomposition" in res.data
    assert b"1. Original Cropped Face" in res.data
    assert b"2. Raw Grad-CAM (JET Spectrum)" in res.data
    assert b"3. Decision Hotspot Overlay" in res.data
    assert b"Facial Zone Gradient Concentration" in res.data
    assert b"Scientific Disclaimer:" in res.data

    with app.app_context():
        scan = Scan.query.filter_by(user_id=user_id).first()
        assert scan is not None
        assert scan.media_type == "image"
        assert scan.analysis_mode == "gradcam-xai"
        assert scan.status == "completed"

        face_res = FaceResult.query.filter_by(scan_id=scan.id).first()
        assert face_res is not None
        assert face_res.gradcam_path is not None
        assert face_res.face_crop_path is not None

def test_direct_gradcam_class_contract(app, sample_face_image):
    """Direct contract test for GradCAM engine backpropagation mathematics"""
    predictor = DeepfakePredictor()
    gradcam = GradCAM(predictor.model)

    img = cv2.imread(sample_face_image)
    crop, _, _, _, _ = predictor.detect_and_crop_face(img)
    cam_data = gradcam.generate(crop)

    assert "heatmap_raw" in cam_data
    assert "heatmap_jet" in cam_data
    assert "overlay_bgr" in cam_data
    assert "target_class" in cam_data
    assert "class_name" in cam_data
    assert "primary_focus" in cam_data
    assert "zone_distribution" in cam_data

    # Mathematical constraints
    raw = cam_data["heatmap_raw"]
    assert raw.shape == (crop.shape[0], crop.shape[1])
    assert float(np.min(raw)) >= 0.0
    assert float(np.max(raw)) <= 1.0

    jet = cam_data["heatmap_jet"]
    assert jet.shape == crop.shape

    overlay = cam_data["overlay_bgr"]
    assert overlay.shape == crop.shape

    assert cam_data["class_name"] in ("REAL", "FAKE")
    zones = cam_data["zone_distribution"]
    assert "upper_eyes" in zones
    assert "mid_cheeks" in zones
    assert "lower_mouth" in zones
