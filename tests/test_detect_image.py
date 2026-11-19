"""
FACEGUARD AI - Single Image Detection Test Suite
Module: tests/test_detect_image.py
"""
import os
import io
import pytest
import numpy as np
import cv2
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan, FaceResult
from faceguard.core.detector import DeepfakePredictor

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
def sample_test_image(tmp_path):
    """Generates a synthetic test face image in PNG format"""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 180
    # Draw simple facial features to test Haar cascade & fallback
    cv2.circle(img, (100, 100), 60, (200, 180, 160), -1)  # Head
    cv2.circle(img, (80, 85), 10, (50, 50, 50), -1)       # Left eye
    cv2.circle(img, (120, 85), 10, (50, 50, 50), -1)      # Right eye
    cv2.ellipse(img, (100, 125), (25, 12), 0, 0, 180, (40, 40, 200), 3) # Mouth

    test_file = tmp_path / "test_portrait.jpg"
    cv2.imwrite(str(test_file), img)
    return str(test_file)

def test_detect_image_requires_login(client):
    """Anonymous visitors cannot access detection endpoints"""
    response = client.get("/detect/image")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_detect_image_page_renders_for_logged_in_user(app, client):
    """Logged-in users can load image scan page"""
    with app.app_context():
        user = User(full_name="David Tester", email="david@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "david@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/image")
    assert res.status_code == 200
    assert b"Verify Facial Authenticity" in res.data
    assert b"Run Deepfake Verification" in res.data
    assert b"Standard Balanced Mode" in res.data

def test_detect_image_rejects_empty_or_invalid_file(app, client):
    """Rejects empty submissions or unsupported file formats"""
    with app.app_context():
        user = User(full_name="Eva Guard", email="eva@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "eva@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty file
    res_empty = client.post("/detect/image", data={}, follow_redirects=True)
    assert res_empty.status_code == 200
    assert b"Please choose a valid JPG or PNG" in res_empty.data

    # Invalid extension
    invalid_data = {
        "image": (io.BytesIO(b"fake executable code"), "malicious.exe")
    }
    res_invalid = client.post("/detect/image", data=invalid_data, follow_redirects=True)
    assert res_invalid.status_code == 200
    assert b"Unsupported file type" in res_invalid.data

def test_detect_image_upload_and_database_persistence(app, client, sample_test_image):
    """Tests end-to-end image upload, neural prediction, forensics, and database persistence"""
    with app.app_context():
        user = User(full_name="Frank Inspector", email="frank@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={"email": "frank@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(sample_test_image, "rb") as f:
        file_bytes = f.read()

    data = {
        "image": (io.BytesIO(file_bytes), "test_portrait.jpg"),
        "mode": "standard"
    }

    res = client.post("/detect/image", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert (b"Verified Authentic Face" in res.data) or (b"Deepfake Manipulation Detected" in res.data)
    assert b"Physical &amp; Optical Diagnostics" in res.data or b"Physical & Optical Diagnostics" in res.data
    assert b"Forensic Audit Metadata" in res.data

    # Check database records
    with app.app_context():
        scan = Scan.query.filter_by(user_id=user_id).first()
        assert scan is not None
        assert scan.media_type == "image"
        assert scan.original_filename == "test_portrait.jpg"
        assert scan.overall_prediction in ("REAL", "FAKE")
        assert scan.overall_confidence > 0.0
        assert scan.status == "completed"
        assert scan.sha256 is not None
        assert len(scan.sha256) == 64

        face_res = FaceResult.query.filter_by(scan_id=scan.id).first()
        assert face_res is not None
        assert face_res.prediction in ("REAL", "FAKE")
        assert face_res.sensor_variance is not None
        assert face_res.fft_ratio is not None
        assert face_res.ela_mean is not None
        assert face_res.chroma_score is not None

def test_direct_predictor_execution(app, sample_test_image):
    """Tests DeepfakePredictor directly for contract and schema adherence"""
    predictor = DeepfakePredictor()
    result = predictor.predict(sample_test_image, mode="standard", save_artifacts=False)

    assert "prediction" in result
    assert result["prediction"] in ("REAL", "FAKE")
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 100.0
    assert "real_probability" in result
    assert "fake_probability" in result
    assert "forensics" in result
    assert "sensor_noise_variance" in result["forensics"]
    assert "frequency_fft_ratio" in result["forensics"]
    assert "ela_mean" in result["forensics"]
    assert "chromatic_coherence" in result["forensics"]
    assert "sha256" in result
    assert len(result["sha256"]) == 64
