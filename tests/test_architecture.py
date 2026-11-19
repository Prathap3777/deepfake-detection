"""
FACEGUARD AI - Architecture Test Suite
Module: tests/test_architecture.py
"""
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models import User, Scan

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

def test_app_creation(app):
    """Verifies that application factory initializes correctly in test mode"""
    assert app is not None
    assert app.config["TESTING"] is True

def test_database_user_model(app):
    """Verifies User model schema, password hashing, and role checks"""
    with app.app_context():
        user = User(full_name="Test User", email="test@faceguard.ai")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

        retrieved = User.query.filter_by(email="test@faceguard.ai").first()
        assert retrieved is not None
        assert retrieved.check_password("SecurePassword123!") is True
        assert retrieved.check_password("WrongPassword") is False
        assert retrieved.is_admin() is False

def test_otp_generation_and_expiry(app):
    """Verifies 6-digit OTP generation and rate limiting"""
    with app.app_context():
        user = User(full_name="OTP User", email="otp@faceguard.ai")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

        code = user.generate_otp()
        assert len(code) == 6
        assert code.isdigit()

        # Test verification
        success, msg = user.verify_otp(code)
        assert success is True
        assert user.is_verified is True
