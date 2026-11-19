"""
FACEGUARD AI - Administration & Security Audit Test Suite
Module: tests/test_admin.py
"""
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan
from faceguard.models.audit import AuditLog

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

def test_admin_routes_require_authentication(client):
    """Anonymous visitors are redirected to the login portal"""
    for route in ["/admin/", "/admin/audit", "/admin/users"]:
        res = client.get(route)
        assert res.status_code == 302
        assert "/auth/login" in res.headers["Location"]

def test_admin_routes_forbidden_for_regular_users(app, client):
    """Authenticated non-admin users receive HTTP 403 Forbidden"""
    with app.app_context():
        regular_user = User(full_name="Regular Joe", email="joe@faceguard.ai", is_verified=True, role="user")
        regular_user.set_password("SecurePass123!")
        db.session.add(regular_user)
        db.session.commit()

    client.post("/auth/login", data={"email": "joe@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    for route in ["/admin/", "/admin/audit", "/admin/users"]:
        res = client.get(route)
        assert res.status_code == 403

def test_admin_overview_renders_for_admin(app, client):
    """Platform administrators can access the control panel and view system stats"""
    with app.app_context():
        admin = User(full_name="Commander Root", email="root@faceguard.ai", is_verified=True, role="admin")
        admin.set_password("AdminPass123!")
        target_user = User(full_name="Target Alpha", email="alpha@faceguard.ai", is_verified=True, role="user")
        target_user.set_password("UserPass123!")
        db.session.add_all([admin, target_user])
        db.session.commit()

        # Add a test scan
        scan = Scan(
            user_id=target_user.id,
            media_type="image",
            original_filename="threat.jpg",
            saved_filename="threat_uuid.jpg",
            overall_prediction="FAKE",
            overall_confidence=97.5,
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()

    client.post("/auth/login", data={"email": "root@faceguard.ai", "password": "AdminPass123!"}, follow_redirects=True)
    res = client.get("/admin/")
    assert res.status_code == 200
    assert b"Security Control Center" in res.data or b"Platform Health" in res.data
    assert b"AI Inference Engine" in res.data
    assert b"threat.jpg" in res.data
    assert b"Target Alpha" in res.data

def test_admin_audit_logs_and_filtering(app, client):
    """Admin can inspect the immutable audit trail and filter by action or query"""
    with app.app_context():
        admin = User(full_name="Auditor General", email="auditor@faceguard.ai", is_verified=True, role="admin")
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()

        # Insert audit entries
        log1 = AuditLog(user_id=admin.id, action="user_login", ip_address="192.168.1.100", details="Successful login")
        log2 = AuditLog(user_id=None, action="failed_login_attempt", ip_address="10.0.0.55", details="Bad password")
        db.session.add_all([log1, log2])
        db.session.commit()

    client.post("/auth/login", data={"email": "auditor@faceguard.ai", "password": "AdminPass123!"}, follow_redirects=True)

    # All logs
    res = client.get("/admin/audit")
    assert res.status_code == 200
    assert b"192.168.1.100" in res.data
    assert b"10.0.0.55" in res.data

    # Filter by action
    res_filtered = client.get("/admin/audit?action=failed_login_attempt")
    assert res_filtered.status_code == 200
    assert b"10.0.0.55" in res_filtered.data

    # Search by IP
    res_search = client.get("/admin/audit?q=192.168.1.100")
    assert res_search.status_code == 200
    assert b"192.168.1.100" in res_search.data

def test_admin_user_management_and_role_toggle(app, client):
    """Admin can view user directory, promote/demote roles, and cannot demote self"""
    with app.app_context():
        admin = User(full_name="Admin Chief", email="chief@faceguard.ai", is_verified=True, role="admin")
        admin.set_password("AdminPass123!")
        member = User(full_name="Member One", email="member@faceguard.ai", is_verified=False, role="user")
        member.set_password("MemberPass123!")
        db.session.add_all([admin, member])
        db.session.commit()
        member_id = member.id
        admin_id = admin.id

    client.post("/auth/login", data={"email": "chief@faceguard.ai", "password": "AdminPass123!"}, follow_redirects=True)

    # View user directory
    res = client.get("/admin/users")
    assert res.status_code == 200
    assert b"Member One" in res.data
    assert b"member@faceguard.ai" in res.data

    # Promote Member to Admin
    toggle_res = client.post(f"/admin/users/{member_id}/toggle-role", follow_redirects=True)
    assert toggle_res.status_code == 200
    with app.app_context():
        updated_member = db.session.get(User, member_id)
        assert updated_member.role == "admin"

    # Attempt to demote self (must be rejected)
    self_res = client.post(f"/admin/users/{admin_id}/toggle-role", follow_redirects=True)
    assert self_res.status_code == 200
    assert b"You cannot alter your own administrative role" in self_res.data
    with app.app_context():
        still_admin = db.session.get(User, admin_id)
        assert still_admin.role == "admin"

def test_admin_user_status_toggle_and_delete(app, client):
    """Admin can toggle verification status and purge user accounts"""
    with app.app_context():
        admin = User(full_name="Admin Sec", email="sec@faceguard.ai", is_verified=True, role="admin")
        admin.set_password("AdminPass123!")
        victim = User(full_name="Victim Bot", email="bot@faceguard.ai", is_verified=False, role="user")
        victim.set_password("BotPass123!")
        db.session.add_all([admin, victim])
        db.session.commit()
        victim_id = victim.id
        admin_id = admin.id

    client.post("/auth/login", data={"email": "sec@faceguard.ai", "password": "AdminPass123!"}, follow_redirects=True)

    # Toggle status to verified
    stat_res = client.post(f"/admin/users/{victim_id}/toggle-status", follow_redirects=True)
    assert stat_res.status_code == 200
    with app.app_context():
        updated_victim = db.session.get(User, victim_id)
        assert updated_victim.is_verified is True

    # Attempt to delete self (must be rejected)
    self_del = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=True)
    assert self_del.status_code == 200
    assert b"You cannot delete your own administrative account" in self_del.data

    # Delete victim account
    del_res = client.post(f"/admin/users/{victim_id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    with app.app_context():
        deleted = db.session.get(User, victim_id)
        assert deleted is None
