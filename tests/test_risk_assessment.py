"""
FACEGUARD AI - AI Risk Assessment Test Suite
Module: tests/test_risk_assessment.py
"""
import io
import os
import pytest
import numpy as np
import cv2
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan
from faceguard.core.risk import compute_risk_assessment

@pytest.fixture
def app(tmp_path):
    app = create_app(TestingConfig)
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
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
    """Creates a sample test face image"""
    img_path = str(tmp_path / "test_face_risk.jpg")
    img_bgr = np.zeros((150, 150, 3), dtype=np.uint8)
    cv2.circle(img_bgr, (75, 75), 50, (190, 170, 140), -1)
    noise = np.random.normal(0, 12, img_bgr.shape).astype(np.uint8)
    img_bgr = cv2.add(img_bgr, noise)
    cv2.imwrite(img_path, img_bgr)
    return img_path

def test_risk_page_requires_login(client):
    """Anonymous visitors must be redirected to login"""
    res = client.get("/detect/risk")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_risk_page_renders_for_logged_in_user(app, client):
    """Authenticated users can access the risk assessment interface"""
    with app.app_context():
        user = User(full_name="Risk Auditor", email="auditor@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "auditor@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/risk")
    assert res.status_code == 200
    assert b"AI Risk Assessment &amp; Priority Score" in res.data or b"AI Risk Assessment & Priority Score" in res.data
    assert b"Calculate Explainable Risk Score" in res.data

def test_risk_rejects_empty_or_invalid_file(app, client):
    """Empty or disallowed files are rejected gracefully"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty
    res = client.post("/detect/risk", data={}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please choose an image file" in res.data

    # Bad extension
    bad_file = (io.BytesIO(b"binary"), "exploit.sh")
    res_bad = client.post("/detect/risk", data={"image": bad_file}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Unsupported file type" in res_bad.data

def test_risk_assessment_calculation_end_to_end(app, client, sample_face_image):
    """Submits image and validates multi-signal risk breakdown generation"""
    with app.app_context():
        user = User(full_name="Risk Analyst", email="analyst@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "analyst@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(sample_face_image, "rb") as f:
        file_bytes = io.BytesIO(f.read())

    res = client.post(
        "/detect/risk",
        data={"image": (file_bytes, "test_face_risk.jpg")},
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert res.status_code == 200
    assert b"Executive Forensic Risk Evaluation" in res.data
    assert b"Risk Index / 100" in res.data
    assert b"Review Priority" in res.data
    assert b"Scoring Methodology &amp; Mathematical Formulation" in res.data or b"Scoring Methodology & Mathematical Formulation" in res.data

def test_risk_inspect_existing_scan(app, client, sample_face_image):
    """Validates inspecting historical scan via ?scan=<uuid>"""
    saved_name = "test_hist_scan.jpg"
    dest_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_name)
    with open(sample_face_image, "rb") as src, open(dest_path, "wb") as dst:
        dst.write(src.read())

    with app.app_context():
        user = User(full_name="Inspector", email="inspect@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            scan_uuid="scan-risk-uuid-999",
            media_type="image",
            original_filename="historic_face.jpg",
            saved_filename=saved_name,
            overall_prediction="REAL",
            overall_confidence=92.5,
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()

    client.post("/auth/login", data={"email": "inspect@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/risk?scan=scan-risk-uuid-999")
    assert res.status_code == 200
    assert b"historic_face.jpg" in res.data
    assert b"Executive Forensic Risk Evaluation" in res.data

def test_risk_scoring_mathematical_contract():
    """Directly tests mathematical boundaries, priority bands, and factor attribution"""
    # Case 1: High Threat Deepfake
    fake_assessment = compute_risk_assessment(
        cnn_prediction="FAKE",
        cnn_confidence=96.0,
        sensor_variance=8.0,      # Extreme artificial smoothness (+18)
        fft_ratio=0.35,           # Severe spectral anomaly (+13)
        ela_uniformity=3.2,       # Non-uniform compression (+10)
        chroma_score=0.62,        # Chromatic boundary shift (+6)
        has_exif=False            # Missing EXIF (+5)
    )
    assert fake_assessment["risk_score"] >= 75.0
    assert fake_assessment["review_priority"] == "High Review Priority"
    assert fake_assessment["priority_class"] == "danger"
    assert len(fake_assessment["contributing_factors"]) >= 4

    # Case 2: Authentic Photographic Capture
    real_assessment = compute_risk_assessment(
        cnn_prediction="REAL",
        cnn_confidence=95.0,
        sensor_variance=65.0,     # Natural sensor grain
        fft_ratio=0.74,           # Normal optical radial decay
        ela_uniformity=1.1,       # Uniform compression gradient
        chroma_score=0.91,        # Coherent RGB sensors
        has_exif=True             # Verified hardware tags
    )
    assert real_assessment["risk_score"] < 25.0
    assert real_assessment["review_priority"] == "Lower Review Priority"
    assert real_assessment["priority_class"] == "success"
    assert len(real_assessment["mitigating_factors"]) >= 4

    # Boundary safety
    assert 0.0 <= fake_assessment["risk_score"] <= 100.0
    assert 0.0 <= real_assessment["risk_score"] <= 100.0
    assert len(fake_assessment["missing_evidence"]) > 0
