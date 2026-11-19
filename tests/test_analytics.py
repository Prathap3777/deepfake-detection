"""
FACEGUARD AI - Forensic Analytics & Model Performance Test Suite
Module: tests/test_analytics.py
"""
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan, FaceResult

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

def test_analytics_requires_login(client):
    """Anonymous visitors cannot access analytics dashboard"""
    response = client.get("/analytics/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_analytics_page_renders_for_logged_in_user(app, client):
    """Authenticated users can view analytics dashboard and confusion matrix benchmark"""
    with app.app_context():
        user = User(full_name="Wendy Stats", email="wendy@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "wendy@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/analytics/")
    assert res.status_code == 200
    assert b"Forensic Analytics &amp; Benchmark Telemetry" in res.data or b"Forensic Analytics & Benchmark Telemetry" in res.data
    assert b"ResNet-18 Benchmark Evaluation &amp; Confusion Matrix" in res.data or b"ResNet-18 Benchmark Evaluation & Confusion Matrix" in res.data
    assert b"True Positive (TP)" in res.data
    assert b"Data Leakage Prevention:" in res.data

def test_analytics_metrics_computation(app, client):
    """Validates metrics aggregation and threat rate calculations"""
    with app.app_context():
        user = User(full_name="Xavier Telemetry", email="xavier@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        # Add 3 REAL images, 1 FAKE video -> 4 scans, 25% threat rate
        s1 = Scan(user_id=user.id, media_type="image", original_filename="p1.jpg", saved_filename="s1.jpg", overall_prediction="REAL", overall_confidence=95.0, status="completed")
        s2 = Scan(user_id=user.id, media_type="image", original_filename="p2.jpg", saved_filename="s2.jpg", overall_prediction="REAL", overall_confidence=92.0, status="completed")
        s3 = Scan(user_id=user.id, media_type="image", original_filename="p3.jpg", saved_filename="s3.jpg", overall_prediction="REAL", overall_confidence=96.0, status="completed")
        s4 = Scan(user_id=user.id, media_type="video", original_filename="v1.mp4", saved_filename="s4.mp4", overall_prediction="FAKE", overall_confidence=89.0, status="completed")
        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        # Add face results
        f1 = FaceResult(scan_id=s1.id, face_index=1, prediction="REAL", confidence=95.0, sensor_variance=70.0, fft_ratio=0.75, ela_mean=12.0, chroma_score=0.91)
        db.session.add(f1)
        db.session.commit()

    client.post("/auth/login", data={"email": "xavier@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/analytics/")
    assert res.status_code == 200
    assert b"25.0%" in res.data  # Threat rate

def test_analytics_summary_api(app, client):
    """Verifies REST API summary endpoint serialization"""
    with app.app_context():
        user = User(full_name="Yara API", email="yara@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        s1 = Scan(user_id=user.id, media_type="image", original_filename="y1.jpg", saved_filename="y1.jpg", overall_prediction="REAL", overall_confidence=90.0, status="completed")
        db.session.add(s1)
        db.session.commit()

    client.post("/auth/login", data={"email": "yara@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    api_res = client.get("/analytics/api/summary")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert data["success"] is True
    assert data["total_scans"] == 1
    assert data["real_scans"] == 1
    assert data["fake_scans"] == 0
    assert data["threat_percentage"] == 0.0
