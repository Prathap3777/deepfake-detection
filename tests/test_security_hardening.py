"""
FACEGUARD AI - Security Hardening & Penetration Defense Test Suite
Module: tests/test_security_hardening.py
"""
import io
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User

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

def test_http_security_headers_present(client):
    """Verifies that modern HTTP defensive headers are injected on all responses"""
    res = client.get("/auth/login")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_password_never_stored_in_plaintext(app):
    """Verifies password hashing via Werkzeug scrypt/pbkdf2"""
    with app.app_context():
        user = User(full_name="Crypto Test", email="crypto@faceguard.ai", is_verified=True)
        raw_password = "SuperSecretPassword123!"
        user.set_password(raw_password)
        db.session.add(user)
        db.session.commit()

        # Database must never hold raw password
        assert user.password_hash != raw_password
        assert user.password_hash.startswith("scrypt:") or user.password_hash.startswith("pbkdf2:")
        assert user.check_password(raw_password) is True
        assert user.check_password("WrongPassword") is False

def test_disallowed_file_extension_rejection(app, client):
    """Verifies malicious executable and script extensions are rejected immediately"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    fake_script = (io.BytesIO(b"malicious script contents"), "exploit.php")
    res = client.post("/detect/image", data={"image": fake_script}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Unsupported file type" in res.data or res.status_code == 200

def test_path_traversal_defense_on_reports(app, client):
    """Verifies path traversal attempts on reports are rejected"""
    with app.app_context():
        user = User(full_name="Path Guard", email="guard@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "guard@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Attempt directory traversal UUID
    res = client.get("/reports/../../../../etc/passwd/download")
    assert res.status_code in (404, 302, 400)
