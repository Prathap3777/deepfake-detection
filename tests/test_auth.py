"""
FACEGUARD AI - Authentication & OTP Test Suite
Module: tests/test_auth.py
"""
import pytest
from datetime import datetime, timedelta, timezone
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User, get_utc_now

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

def test_user_registration_creates_otp(app, client):
    """Tests registration flow and OTP creation"""
    response = client.post("/auth/register", data={
        "full_name": "Alice Smith",
        "email": "alice@faceguard.ai",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="alice@faceguard.ai").first()
        assert user is not None
        assert user.is_verified is False
        assert user.otp_code is not None
        assert len(user.otp_code) == 6

def test_email_verification_success(app, client):
    """Tests successful OTP confirmation activating account"""
    with app.app_context():
        user = User(full_name="Bob User", email="bob@faceguard.ai", is_verified=False)
        user.set_password("Password123!")
        otp = user.generate_otp()
        db.session.add(user)
        db.session.commit()

    response = client.post(f"/auth/verify-email?email=bob@faceguard.ai", data={
        "otp_code": otp
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="bob@faceguard.ai").first()
        assert user.is_verified is True
        assert user.otp_code is None

def test_email_verification_wrong_code(app, client):
    """Tests failed verification attempt counter"""
    with app.app_context():
        user = User(full_name="Charlie User", email="charlie@faceguard.ai", is_verified=False)
        user.set_password("Password123!")
        user.generate_otp()
        db.session.add(user)
        db.session.commit()

    response = client.post(f"/auth/verify-email?email=charlie@faceguard.ai", data={
        "otp_code": "000000"
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="charlie@faceguard.ai").first()
        assert user.is_verified is False
        assert user.otp_attempts == 1

def test_unverified_user_cannot_login(app, client):
    """Tests that unverified user login triggers OTP redirect"""
    with app.app_context():
        user = User(full_name="Diana User", email="diana@faceguard.ai", is_verified=False)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "email": "diana@faceguard.ai",
        "password": "Password123!"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "verify-email" in response.headers["Location"]

def test_verified_user_login_and_logout(app, client):
    """Tests verified login and secure session clearance"""
    with app.app_context():
        user = User(full_name="Evan User", email="evan@faceguard.ai", is_verified=True)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    # Login
    response = client.post("/auth/login", data={
        "email": "evan@faceguard.ai",
        "password": "Password123!"
    }, follow_redirects=True)
    assert response.status_code == 200

    # Logout
    logout_resp = client.get("/auth/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"signed out" in logout_resp.data

def test_password_reset_workflow(app, client):
    """Tests forgot password request and code-based reset"""
    with app.app_context():
        user = User(full_name="Frank User", email="frank@faceguard.ai", is_verified=True)
        user.set_password("OldPassword123!")
        db.session.add(user)
        db.session.commit()

    # Request Reset
    client.post("/auth/forgot-password", data={"email": "frank@faceguard.ai"}, follow_redirects=True)

    with app.app_context():
        user = User.query.filter_by(email="frank@faceguard.ai").first()
        assert user.reset_token is not None
        token = user.reset_token

    # Submit New Password
    resp = client.post(f"/auth/reset-password?email=frank@faceguard.ai", data={
        "otp_code": token,
        "new_password": "NewSecurePassword456!",
        "confirm_new_password": "NewSecurePassword456!"
    }, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="frank@faceguard.ai").first()
        assert user.check_password("NewSecurePassword456!") is True
        assert user.check_password("OldPassword123!") is False
        assert user.reset_token is None
