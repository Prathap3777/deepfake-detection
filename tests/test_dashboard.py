"""
FACEGUARD AI - Dashboard & Frontend Test Suite
Module: tests/test_dashboard.py
"""
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan

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

def test_unauthenticated_overview_redirects_to_login(client):
    """Unauthenticated users must be redirected to the login page"""
    response = client.get("/overview")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_authenticated_overview_renders(app, client):
    """Authenticated and verified user can view overview dashboard"""
    with app.app_context():
        user = User(full_name="Alice Security", email="alice@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    # Login user
    login_res = client.post("/auth/login", data={
        "email": "alice@faceguard.ai",
        "password": "SecurePass123!"
    }, follow_redirects=True)
    assert login_res.status_code == 200

    overview_res = client.get("/overview")
    assert overview_res.status_code == 200
    assert b"Security Overview" in overview_res.data
    assert b"Total Scans" in overview_res.data
    assert b"Verified Authentic" in overview_res.data
    assert b"Deepfakes Flagged" in overview_res.data
    assert b"PyTorch ResNet-18 Online" in overview_res.data

def test_overview_statistics_with_scans(app, client):
    """Overview dashboard calculates scan totals, real/fake counts, and confidence properly"""
    with app.app_context():
        user = User(full_name="Bob Forensic", email="bob@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        # Add 3 test scans
        scan1 = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="portrait_real.jpg",
            saved_filename="portrait_real_uuid.jpg",
            face_count=1,
            overall_prediction="REAL",
            overall_confidence=95.0,
            status="completed"
        )
        scan2 = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="avatar_fake.png",
            saved_filename="avatar_fake_uuid.png",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=91.0,
            status="completed"
        )
        scan3 = Scan(
            user_id=user.id,
            media_type="video",
            original_filename="speech_fake.mp4",
            saved_filename="speech_fake_uuid.mp4",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=87.0,
            status="completed"
        )
        db.session.add_all([scan1, scan2, scan3])
        db.session.commit()

    # Login
    client.post("/auth/login", data={
        "email": "bob@faceguard.ai",
        "password": "SecurePass123!"
    }, follow_redirects=True)

    overview_res = client.get("/overview")
    assert overview_res.status_code == 200
    # Check that 3 scans, 1 real, 2 fake, and avg confidence (91.0) appear in response
    assert b"portrait_real.jpg" in overview_res.data
    assert b"avatar_fake.png" in overview_res.data
    assert b"speech_fake.mp4" in overview_res.data
    assert b"91.0%" in overview_res.data

def test_settings_page_get_and_post(app, client):
    """Settings page renders and accepts preference updates"""
    with app.app_context():
        user = User(full_name="Charlie Admin", email="charlie@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={
        "email": "charlie@faceguard.ai",
        "password": "SecurePass123!"
    }, follow_redirects=True)

    # GET settings
    get_res = client.get("/settings")
    assert get_res.status_code == 200
    assert b"Preferences &amp; Model Tuning" in get_res.data or b"Preferences & Model Tuning" in get_res.data

    # POST settings
    post_res = client.post("/settings", data={
        "theme": "light",
        "sensitivity": "high",
        "email_alerts": "y"
    }, follow_redirects=True)
    assert post_res.status_code == 200
    assert b"Your preferences have been successfully updated." in post_res.data

def test_admin_sidebar_links_visibility(app, client):
    """Regular users do not see admin links; admin users see admin section"""
    with app.app_context():
        normal_user = User(full_name="Normal User", email="normal@faceguard.ai", is_verified=True, role="user")
        normal_user.set_password("SecurePass123!")
        admin_user = User(full_name="Super Admin", email="admin@faceguard.ai", is_verified=True, role="admin")
        admin_user.set_password("SecurePass123!")
        db.session.add_all([normal_user, admin_user])
        db.session.commit()

    # Login as normal user
    client.post("/auth/login", data={"email": "normal@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_normal = client.get("/overview")
    assert b"Security Audit Logs" not in res_normal.data
    assert b"Administration" not in res_normal.data

    client.get("/auth/logout", follow_redirects=True)

    # Login as admin user
    client.post("/auth/login", data={"email": "admin@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_admin = client.get("/overview")
    assert b"Security Audit Logs" in res_admin.data
    assert b"Administration" in res_admin.data
