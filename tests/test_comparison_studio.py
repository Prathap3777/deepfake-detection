"""
FACEGUARD AI - Detection Comparison Studio Test Suite
Module: tests/test_comparison_studio.py
"""
import io
import os
import json
import pytest
import numpy as np
import cv2
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan
from faceguard.core.comparator import compare_two_images

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
def pair_of_images(tmp_path):
    """Creates two distinct synthetic test images for comparison"""
    path_a = str(tmp_path / "comp_img_a.jpg")
    path_b = str(tmp_path / "comp_img_b.jpg")

    img_a = np.zeros((180, 180, 3), dtype=np.uint8)
    cv2.circle(img_a, (90, 90), 55, (210, 180, 160), -1)
    noise_a = np.random.normal(0, 10, img_a.shape).astype(np.uint8)
    img_a = cv2.add(img_a, noise_a)
    cv2.imwrite(path_a, img_a)

    img_b = np.zeros((180, 180, 3), dtype=np.uint8)
    cv2.circle(img_b, (90, 90), 50, (180, 150, 130), -1)
    noise_b = np.random.normal(0, 8, img_b.shape).astype(np.uint8)
    img_b = cv2.add(img_b, noise_b)
    cv2.imwrite(path_b, img_b)

    return path_a, path_b

def test_comparison_studio_requires_login(client):
    """Anonymous visitors must be redirected to login"""
    res = client.get("/detect/compare")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_comparison_studio_renders_for_logged_in_user(app, client):
    """Logged in users can view the comparison studio interface"""
    with app.app_context():
        user = User(full_name="Studio Auditor", email="studio@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "studio@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/compare")
    assert res.status_code == 200
    assert b"Detection Comparison Studio" in res.data
    assert b"Image A (Reference / Baseline)" in res.data
    assert b"Image B (Target / Suspect)" in res.data

def test_comparison_rejects_missing_inputs(app, client):
    """Rejects submissions without both images"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.post("/detect/compare", data={}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please provide two valid images" in res.data

def test_comparison_execution_end_to_end(app, client, pair_of_images):
    """Submits two images and verifies side-by-side analysis, split slider, and metrics"""
    path_a, path_b = pair_of_images
    with app.app_context():
        user = User(full_name="Forensic Comparator", email="comp@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "comp@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        data = {
            "image_a": (io.BytesIO(fa.read()), "comp_img_a.jpg"),
            "image_b": (io.BytesIO(fb.read()), "comp_img_b.jpg")
        }
        res = client.post("/detect/compare", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert res.status_code == 200
    assert b"Interactive Split Comparison Slider" in res.data
    assert b"Multi-Domain Metrics Matrix" in res.data
    assert b"comp_img_a.jpg" in res.data
    assert b"comp_img_b.jpg" in res.data
    assert b"Download Comparison PDF Dossier" in res.data
    assert b"Visual Difference vs Evidence of Manipulation" in res.data

def test_comparison_with_historical_scans(app, client, pair_of_images):
    """Validates comparing two previously saved historical scans"""
    path_a, path_b = pair_of_images
    saved_a = "hist_a.jpg"
    saved_b = "hist_b.jpg"

    with open(path_a, "rb") as fa, open(os.path.join(app.config["UPLOAD_FOLDER"], saved_a), "wb") as out_a:
        out_a.write(fa.read())
    with open(path_b, "rb") as fb, open(os.path.join(app.config["UPLOAD_FOLDER"], saved_b), "wb") as out_b:
        out_b.write(fb.read())

    with app.app_context():
        user = User(full_name="Archive Specialist", email="archive@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        s1 = Scan(user_id=user.id, scan_uuid="scan-comp-111", media_type="image", original_filename="arch_a.jpg", saved_filename=saved_a, overall_prediction="REAL", overall_confidence=93.0, status="completed")
        s2 = Scan(user_id=user.id, scan_uuid="scan-comp-222", media_type="image", original_filename="arch_b.jpg", saved_filename=saved_b, overall_prediction="REAL", overall_confidence=91.0, status="completed")
        db.session.add_all([s1, s2])
        db.session.commit()

    client.post("/auth/login", data={"email": "archive@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.post("/detect/compare", data={"scan_id_a": "scan-comp-111", "scan_id_b": "scan-comp-222"}, follow_redirects=True)

    assert res.status_code == 200
    assert b"arch_a.jpg" in res.data
    assert b"arch_b.jpg" in res.data
    assert b"Interactive Split Comparison Slider" in res.data

def test_comparison_pdf_export_endpoint(app, client, pair_of_images):
    """Validates generating and exporting comparison PDF dossier"""
    path_a, path_b = pair_of_images
    with app.app_context():
        user = User(full_name="PDF Requester", email="pdfreq@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "pdfreq@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # First run comparator to get payload
    comp_data = compare_two_images(path_a, path_b, app.config["UPLOAD_FOLDER"], "A.jpg", "B.jpg")
    json_payload = json.dumps(comp_data)

    res = client.post("/detect/compare/export", data={"comparison_data": json_payload})
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert "comparison_dossier.pdf" in res.headers["Content-Disposition"]

def test_direct_comparator_engine_contract(pair_of_images, tmp_path):
    """Directly tests Python unit contract of compare_two_images"""
    path_a, path_b = pair_of_images
    out_dir = str(tmp_path / "comp_out")
    os.makedirs(out_dir, exist_ok=True)

    result = compare_two_images(path_a, path_b, out_dir, "TargetA.jpg", "TargetB.jpg")
    assert "image_a" in result
    assert "image_b" in result
    assert "diff_map" in result
    assert "conf_delta" in result
    assert "risk_delta" in result
    assert isinstance(result["concordant"], bool)
    assert len(result["summary"]) > 0
