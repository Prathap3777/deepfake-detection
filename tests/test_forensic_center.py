"""
FACEGUARD AI - AI Forensic Intelligence Center Test Suite
Module: tests/test_forensic_center.py
"""
import io
import os
import pytest
import numpy as np
import cv2
from PIL import Image
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan
from faceguard.core.forensics import (
    extract_exif_metadata,
    inspect_file_properties,
    generate_full_ela,
    generate_full_fft,
    analyze_full_forensics
)

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
def test_image_file(tmp_path):
    """Creates a synthetic photographic-style test image"""
    img_path = str(tmp_path / "sample_evidence.jpg")
    img_bgr = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(img_bgr, (100, 100), 60, (200, 180, 150), -1)
    # Add noise for sensor variance
    noise = np.random.normal(0, 10, img_bgr.shape).astype(np.uint8)
    img_bgr = cv2.add(img_bgr, noise)
    cv2.imwrite(img_path, img_bgr)
    return img_path

def test_forensics_requires_login(client):
    """Anonymous visitors are redirected to login"""
    res = client.get("/detect/forensics")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_forensics_page_renders_for_logged_in_user(app, client):
    """Authenticated users can view the Forensic Intelligence Center"""
    with app.app_context():
        user = User(full_name="Forensic Agent", email="agent@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "agent@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/forensics")
    assert res.status_code == 200
    assert b"AI Forensic Intelligence Center" in res.data
    assert b"Upload Photographic Evidence" in res.data

def test_forensics_rejects_empty_or_invalid_file(app, client):
    """Rejects empty submissions or unsupported executable files"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty file
    res = client.post("/detect/forensics", data={}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please upload a valid photographic image" in res.data

    # Invalid extension
    bad_file = (io.BytesIO(b"binary payload"), "malware.exe")
    res_bad = client.post("/detect/forensics", data={"image": bad_file}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Unsupported file type" in res_bad.data

def test_forensic_analysis_execution_end_to_end(app, client, test_image_file):
    """Submits evidence image and validates full multi-domain forensic audit report"""
    with app.app_context():
        user = User(full_name="Examiner One", email="examiner@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "examiner@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(test_image_file, "rb") as f:
        file_bytes = io.BytesIO(f.read())

    res = client.post(
        "/detect/forensics",
        data={"image": (file_bytes, "sample_evidence.jpg")},
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert res.status_code == 200
    assert b"Forensic Examination Report" in res.data
    assert b"Error Level Analysis (ELA)" in res.data
    assert b"2D-FFT Fourier Spectrum" in res.data
    assert b"Scientific Methodology &amp; Diagnostic Limitations" in res.data or b"Scientific Methodology & Diagnostic Limitations" in res.data
    assert b"sample_evidence.jpg" in res.data

def test_forensic_inspect_existing_scan(app, client, test_image_file):
    """Validates inspecting an existing scan from detection history via ?scan=<uuid>"""
    saved_name = "test_scan_123.jpg"
    dest_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_name)
    with open(test_image_file, "rb") as src, open(dest_path, "wb") as dst:
        dst.write(src.read())

    with app.app_context():
        user = User(full_name="Investigator Lee", email="lee@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            scan_uuid="scan-uuid-abc-123",
            media_type="image",
            original_filename="original_face.jpg",
            saved_filename=saved_name,
            overall_prediction="REAL",
            overall_confidence=94.0,
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()

    client.post("/auth/login", data={"email": "lee@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/forensics?scan=scan-uuid-abc-123")
    assert res.status_code == 200
    assert b"Forensic Examination Report" in res.data
    assert b"original_face.jpg" in res.data

def test_direct_forensic_functions_contract(test_image_file, tmp_path):
    """Directly tests Python unit contract of all forensic diagnostic functions"""
    upload_folder = str(tmp_path / "artifacts")
    os.makedirs(upload_folder, exist_ok=True)

    # 1. EXIF metadata extraction
    exif = extract_exif_metadata(test_image_file)
    assert "has_exif" in exif
    assert "fields" in exif
    assert isinstance(exif["notes"], list)

    # 2. File container inspection
    props = inspect_file_properties(test_image_file, "sample.jpg")
    assert props["width"] == 200
    assert props["height"] == 200
    assert props["format"] == "JPEG"
    assert props["file_size_bytes"] > 0

    # 3. Full-frame ELA
    ela_id, ela_stats = generate_full_ela(test_image_file, upload_folder)
    assert ela_id is not None
    assert os.path.exists(os.path.join(upload_folder, ela_id))
    assert "mean_error" in ela_stats
    assert "uniformity_ratio" in ela_stats

    # 4. Full-frame 2D-FFT
    fft_id, fft_stats = generate_full_fft(test_image_file, upload_folder)
    assert fft_id is not None
    assert os.path.exists(os.path.join(upload_folder, fft_id))
    assert "high_to_low_ratio" in fft_stats

    # 5. Full forensic audit orchestration
    audit = analyze_full_forensics(test_image_file, "sample.jpg", upload_folder)
    assert len(audit["findings"]) >= 4
    assert "noise_analysis" in audit
    assert "laplacian_variance" in audit["noise_analysis"]
