"""
FACEGUARD AI - Detection History & Audit Test Suite
Module: tests/test_history.py
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

def test_history_requires_login(client):
    """Anonymous visitors cannot access detection history"""
    response = client.get("/history/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_history_list_empty_for_new_user(app, client):
    """New users with zero scans see clean empty state"""
    with app.app_context():
        user = User(full_name="Quinn Empty", email="quinn@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "quinn@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/history/")
    assert res.status_code == 200
    assert b"No Verification Records Found" in res.data
    assert b"Upload Image" in res.data

def test_history_isolation_between_users(app, client):
    """Users must only access and view their own scan records"""
    with app.app_context():
        user_a = User(full_name="Alice User", email="alice_hist@faceguard.ai", is_verified=True, role="user")
        user_a.set_password("SecurePass123!")
        user_b = User(full_name="Bob Private", email="bob_hist@faceguard.ai", is_verified=True, role="user")
        user_b.set_password("SecurePass123!")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        # Add private scan belonging to User B
        scan_b = Scan(
            user_id=user_b.id,
            media_type="image",
            original_filename="bob_secret_photo.jpg",
            saved_filename="bob_secret_uuid.jpg",
            face_count=1,
            overall_prediction="REAL",
            overall_confidence=97.0,
            status="completed"
        )
        db.session.add(scan_b)
        db.session.commit()
        bob_scan_uuid = scan_b.scan_uuid

    # Log in as User A
    client.post("/auth/login", data={"email": "alice_hist@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # 1. User A should not see User B's scan in listing
    res_list = client.get("/history/")
    assert res_list.status_code == 200
    assert b"bob_secret_photo.jpg" not in res_list.data

    # 2. User A cannot view User B's scan details directly (must 404)
    res_detail = client.get(f"/history/{bob_scan_uuid}")
    assert res_detail.status_code == 404

    # 3. User A cannot delete User B's scan (must 404)
    res_del = client.post(f"/history/{bob_scan_uuid}/delete")
    assert res_del.status_code == 404

def test_history_search_and_filters(app, client):
    """Tests keyword search, media type filter, and verdict filters"""
    with app.app_context():
        user = User(full_name="Rachel Searcher", email="rachel@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        s1 = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="passport_real.jpg",
            saved_filename="s1.jpg",
            face_count=1,
            overall_prediction="REAL",
            overall_confidence=95.0,
            status="completed"
        )
        s2 = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="avatar_fake.png",
            saved_filename="s2.png",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=92.0,
            status="completed"
        )
        s3 = Scan(
            user_id=user.id,
            media_type="video",
            original_filename="interview_fake.mp4",
            saved_filename="s3.mp4",
            face_count=3,
            overall_prediction="FAKE",
            overall_confidence=88.0,
            status="completed"
        )
        db.session.add_all([s1, s2, s3])
        db.session.commit()

    client.post("/auth/login", data={"email": "rachel@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # 1. Search by keyword
    res_q = client.get("/history/?q=passport")
    assert res_q.status_code == 200
    assert b"passport_real.jpg" in res_q.data
    assert b"avatar_fake.png" not in res_q.data
    assert b"interview_fake.mp4" not in res_q.data

    # 2. Filter by media type
    res_vid = client.get("/history/?media_type=video")
    assert res_vid.status_code == 200
    assert b"interview_fake.mp4" in res_vid.data
    assert b"passport_real.jpg" not in res_vid.data

    # 3. Filter by verdict REAL
    res_real = client.get("/history/?verdict=REAL")
    assert res_real.status_code == 200
    assert b"passport_real.jpg" in res_real.data
    assert b"avatar_fake.png" not in res_real.data

    # 4. Filter by verdict FAKE
    res_fake = client.get("/history/?verdict=FAKE")
    assert res_fake.status_code == 200
    assert b"avatar_fake.png" in res_fake.data
    assert b"interview_fake.mp4" in res_fake.data
    assert b"passport_real.jpg" not in res_fake.data

def test_history_detail_view_and_delete(app, client):
    """Tests viewing a scan detail page and deleting the scan"""
    with app.app_context():
        user = User(full_name="Sam Inspector", email="sam@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="portrait_audit.jpg",
            saved_filename="portrait_audit_uuid.jpg",
            face_count=1,
            overall_prediction="REAL",
            overall_confidence=96.4,
            sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id
        scan_uuid = scan.scan_uuid

        face = FaceResult(
            scan_id=scan.id,
            face_index=1,
            bbox_x=50,
            bbox_y=60,
            bbox_w=100,
            bbox_h=100,
            prediction="REAL",
            confidence=96.4
        )
        db.session.add(face)
        db.session.commit()

    client.post("/auth/login", data={"email": "sam@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # View details
    res_detail = client.get(f"/history/{scan_uuid}")
    assert res_detail.status_code == 200
    assert b"portrait_audit.jpg" in res_detail.data
    assert b"Forensic Audit Detail #" in res_detail.data
    assert b"Localized Face Sub-Results" in res_detail.data
    assert b"abcdef1234567890" in res_detail.data

    # Delete scan
    res_del = client.post(f"/history/{scan_uuid}/delete", follow_redirects=True)
    assert res_del.status_code == 200
    assert b"has been deleted successfully." in res_del.data

    with app.app_context():
        deleted = Scan.query.filter_by(scan_uuid=scan_uuid).first()
        assert deleted is None
        child_face = FaceResult.query.filter_by(scan_id=scan_id).first()
        assert child_face is None
