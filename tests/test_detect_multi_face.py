"""
FACEGUARD AI - Multiple Face Detection Test Suite
Module: tests/test_detect_multi_face.py
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
def group_test_image(tmp_path):
    """Generates an image with 2 actual face representations tiled horizontally"""
    p1 = os.path.join(BASE_DIR, "dataset", "real", "real_01.jpg")
    p2 = os.path.join(BASE_DIR, "dataset", "real", "real_02.jpg")
    
    if os.path.exists(p1) and os.path.exists(p2):
        img1 = cv2.imread(p1)
        img2 = cv2.imread(p2)
        img1 = cv2.resize(img1, (300, 300))
        img2 = cv2.resize(img2, (300, 300))
        group = np.hstack([img1, img2])
    else:
        # Fallback synthetic portrait pair
        group = np.ones((300, 600, 3), dtype=np.uint8) * 180
        cv2.circle(group, (150, 150), 70, (200, 180, 160), -1)
        cv2.circle(group, (450, 150), 70, (200, 180, 160), -1)

    path = tmp_path / "group_photo.jpg"
    cv2.imwrite(str(path), group)
    return str(path)

@pytest.fixture
def blank_test_image(tmp_path):
    """Generates a solid texture-free image without any human faces"""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 100
    path = tmp_path / "blank_scene.jpg"
    cv2.imwrite(str(path), img)
    return str(path)

def test_multi_face_requires_login(client):
    """Unauthenticated users cannot access multi-face detection route"""
    response = client.get("/detect/multi-face")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_multi_face_page_renders_for_logged_in_user(app, client):
    """Authenticated users can view multi-face upload interface"""
    with app.app_context():
        user = User(full_name="Grace Group", email="grace@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "grace@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/multi-face")
    assert res.status_code == 200
    assert b"Group Photo &amp; Crowd Authenticity Scanner" in res.data or b"Group Photo & Crowd Authenticity Scanner" in res.data
    assert b"Analyze All Faces" in res.data

def test_multi_face_rejects_empty_or_invalid_file(app, client):
    """Rejects empty submissions or invalid file extensions"""
    with app.app_context():
        user = User(full_name="Henry Guard", email="henry@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "henry@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty post
    res_empty = client.post("/detect/multi-face", data={}, follow_redirects=True)
    assert res_empty.status_code == 200
    assert b"Please choose a valid JPG or PNG group image" in res_empty.data

    # Invalid extension
    bad_data = {"image": (io.BytesIO(b"binary data"), "unsupported.pdf")}
    res_bad = client.post("/detect/multi-face", data=bad_data, follow_redirects=True)
    assert res_bad.status_code == 200
    assert b"Unsupported file type" in res_bad.data

def test_multi_face_detection_end_to_end(app, client, group_test_image):
    """Tests end-to-end multi-face detection, per-face inference, and database persistence"""
    with app.app_context():
        user = User(full_name="Ian Multi", email="ian@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={"email": "ian@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(group_test_image, "rb") as f:
        file_bytes = f.read()

    data = {
        "image": (io.BytesIO(file_bytes), "group_photo.jpg"),
        "mode": "standard"
    }

    res = client.post("/detect/multi-face", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert b"Master Annotated Scene" in res.data
    assert b"Individual Subject Breakdown" in res.data
    assert b"Face #1" in res.data

    with app.app_context():
        scan = Scan.query.filter_by(user_id=user_id).first()
        assert scan is not None
        assert scan.media_type == "image"
        assert scan.face_count >= 1
        assert scan.overall_prediction in ("REAL", "FAKE")
        assert scan.status == "completed"

        faces = FaceResult.query.filter_by(scan_id=scan.id).all()
        assert len(faces) == scan.face_count
        for face in faces:
            assert face.prediction in ("REAL", "FAKE")
            assert face.confidence > 0.0
            assert face.face_crop_path is not None

def test_multi_face_zero_faces_handling(app, client, blank_test_image):
    """Gracefully handles scenes where no faces are detected"""
    with app.app_context():
        user = User(full_name="Julia Test", email="julia@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "julia@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(blank_test_image, "rb") as f:
        file_bytes = f.read()

    data = {"image": (io.BytesIO(file_bytes), "blank_scene.jpg"), "mode": "standard"}
    res = client.post("/detect/multi-face", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert res.status_code == 200
    assert (b"No Human Faces Found" in res.data) or (b"No Faces Localized" in res.data) or (b"NO FACES DETECTED" in res.data)

def test_direct_predictor_multi_face_contract(app, group_test_image):
    """Tests DeepfakePredictor.predict_multi_face schema and output keys"""
    predictor = DeepfakePredictor()
    result = predictor.predict_multi_face(group_test_image, mode="standard", save_artifacts=False)

    assert "face_count" in result
    assert "faces" in result
    assert "overall_prediction" in result
    assert "overall_confidence" in result
    assert "real_count" in result
    assert "fake_count" in result
    assert "sha256" in result
    assert len(result["sha256"]) == 64
    assert result["overall_prediction"] in ("REAL", "FAKE", "UNKNOWN")
