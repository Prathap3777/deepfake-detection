"""
FACEGUARD AI - Video Deepfake Detection Test Suite
Module: tests/test_detect_video.py
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
from faceguard.models.scan import Scan, VideoFrame
from faceguard.core.video import analyze_video

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
def sample_test_video(tmp_path):
    """Generates a small 15-frame MP4 video clip containing real face content"""
    face_img_path = os.path.join(BASE_DIR, "dataset", "real", "real_01.jpg")
    if os.path.exists(face_img_path):
        base_frame = cv2.imread(face_img_path)
        base_frame = cv2.resize(base_frame, (256, 256))
    else:
        base_frame = np.ones((256, 256, 3), dtype=np.uint8) * 150
        cv2.circle(base_frame, (128, 128), 60, (200, 180, 160), -1)

    video_path = tmp_path / "test_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (256, 256))

    for _ in range(15):
        out.write(base_frame)

    out.release()
    return str(video_path)

def test_video_requires_login(client):
    """Unauthenticated users cannot access video detection"""
    response = client.get("/detect/video")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_video_page_renders_for_logged_in_user(app, client):
    """Authenticated users can view video uploader page"""
    with app.app_context():
        user = User(full_name="Nancy Video", email="nancy@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "nancy@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/video")
    assert res.status_code == 200
    assert b"Video Deepfake &amp; Face Swap Scanner" in res.data or b"Video Deepfake & Face Swap Scanner" in res.data
    assert b"Analyze Video Frames" in res.data

def test_video_rejects_empty_or_invalid_file(app, client):
    """Rejects empty submissions or unsupported video codecs"""
    with app.app_context():
        user = User(full_name="Oscar Guard", email="oscar@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "oscar@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Empty post
    res_empty = client.post("/detect/video", data={}, follow_redirects=True)
    assert res_empty.status_code == 200
    assert b"Please choose a valid MP4, AVI, or MOV video" in res_empty.data

    # Invalid extension
    bad_data = {"video": (io.BytesIO(b"data"), "malicious.exe")}
    res_bad = client.post("/detect/video", data=bad_data, follow_redirects=True)
    assert res_bad.status_code == 200
    assert b"Unsupported video format" in res_bad.data

def test_video_analysis_end_to_end(app, client, sample_test_video):
    """Tests end-to-end video frame sampling, face inference, and database persistence"""
    with app.app_context():
        user = User(full_name="Peter Stream", email="peter@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={"email": "peter@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    with open(sample_test_video, "rb") as f:
        file_bytes = f.read()

    data = {"video": (io.BytesIO(file_bytes), "sample_clip.mp4")}
    res = client.post("/detect/video", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert res.status_code == 200
    assert (b"AUTHENTIC VIDEO" in res.data) or (b"DEEPFAKE MANIPULATION DETECTED" in res.data)
    assert b"Total Frames" in res.data
    assert b"Face Frames" in res.data
    assert b"Aggregation Methodology" in res.data
    assert b"Sampled Frame Timeline" in res.data

    with app.app_context():
        scan = Scan.query.filter_by(user_id=user_id).first()
        assert scan is not None
        assert scan.media_type == "video"
        assert scan.analysis_mode == "video-frames"
        assert scan.status == "completed"

        frames = VideoFrame.query.filter_by(scan_id=scan.id).all()
        assert len(frames) > 0
        for vf in frames:
            assert vf.timestamp_sec >= 0.0
            assert vf.frame_path is not None
            if vf.face_detected:
                assert vf.prediction in ("REAL", "FAKE")

def test_direct_video_analyzer_contract(app, sample_test_video):
    """Direct contract test for analyze_video schema and output keys"""
    result = analyze_video(sample_test_video, max_frames=10, sample_fps=1)

    assert "total_sampled_frames" in result
    assert result["total_sampled_frames"] > 0
    assert "face_frames_count" in result
    assert "real_frames_count" in result
    assert "fake_frames_count" in result
    assert "overall_prediction" in result
    assert result["overall_prediction"] in ("REAL", "FAKE", "UNKNOWN")
    assert "overall_confidence" in result
    assert "aggregation_method" in result
    assert "frames" in result
    assert len(result["frames"]) == result["total_sampled_frames"]

    first_frame = result["frames"][0]
    assert "frame_index" in first_frame
    assert "timestamp_sec" in first_frame
    assert "timestamp_str" in first_frame
    assert "frame_path" in first_frame
    assert "face_detected" in first_frame
    assert "is_suspicious" in first_frame
