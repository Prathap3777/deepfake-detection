"""
FACEGUARD AI - AI Forensic Chat Assistant Test Suite
Module: tests/test_chat_assistant.py
"""
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan, FaceResult
from faceguard.models.chat import ChatSession, ChatMessage
from faceguard.core.chat import generate_chat_response

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

def test_chat_requires_authentication(client):
    """Anonymous visitors cannot access chat assistant"""
    res = client.get("/chat/")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_chat_page_renders_for_logged_in_user(app, client):
    """Authenticated user accesses chat assistant, auto-spawns default session"""
    with app.app_context():
        user = User(full_name="Agent Dana", email="dana@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "dana@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/chat/")
    assert res.status_code == 200
    assert b"AI Forensic Chat Assistant" in res.data
    assert b"FaceGuard AI Forensic Assistant" in res.data or b"Forensic Consultation" in res.data

def test_chat_session_creation_with_scan_context(app, client):
    """User creates a new consultation explicitly bound to an existing scan"""
    with app.app_context():
        user = User(full_name="Fox Mulder", email="fox@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="threat_ufo.jpg",
            saved_filename="threat_ufo_uuid.jpg",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=94.8,
            risk_score=78.5,
            review_priority="High Review Priority",
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()
        scan_uuid = scan.scan_uuid
        user_id = user.id
        scan_id = scan.id

    client.post("/auth/login", data={"email": "fox@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.post("/chat/new", data={"scan_uuid": scan_uuid}, follow_redirects=True)
    assert res.status_code == 200
    assert b"threat_ufo.jpg" in res.data

    with app.app_context():
        session = ChatSession.query.filter_by(user_id=user_id).first()
        assert session is not None
        assert session.scan_id == scan_id

def test_chat_api_send_and_response_reasoning(app, client):
    """Sending message returns scientifically grounded JSON and saves audit messages"""
    with app.app_context():
        user = User(full_name="Scully AI", email="scully@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="altered_face.jpg",
            saved_filename="altered_face_uuid.jpg",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=96.2,
            risk_score=82.0,
            review_priority="High Review Priority",
            sha256="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()

        face = FaceResult(
            scan_id=scan.id,
            face_index=1,
            prediction="FAKE",
            confidence=96.2,
            sensor_variance=31.2,
            fft_ratio=0.312,
            ela_mean=28.4
        )
        db.session.add(face)
        db.session.commit()

        chat_session = ChatSession(
            user_id=user.id,
            scan_id=scan.id,
            title="Forensic Audit"
        )
        db.session.add(chat_session)
        db.session.commit()
        session_uuid = chat_session.session_uuid
        chat_session_id = chat_session.id

    client.post("/auth/login", data={"email": "scully@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # 1. Ask why classified as fake
    res1 = client.post("/chat/api/send", json={
        "session_uuid": session_uuid,
        "message": "Why was my image classified as fake?"
    })
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["status"] == "success"
    assert "DEEPFAKE" in data1["reply"]
    assert "ResNet-18" in data1["reply"]
    assert "96.2%" in data1["reply"]

    # 2. Ask about heatmap
    res2 = client.post("/chat/api/send", json={
        "session_uuid": session_uuid,
        "message": "Explain the Grad-CAM heatmap and red hotspots"
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert "layer4" in data2["reply"]
    assert "Red" in data2["reply"]

    # 3. Ask about confidence score
    res3 = client.post("/chat/api/send", json={
        "session_uuid": session_uuid,
        "message": "What does my confidence score mean?"
    })
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert "Softmax" in data3["reply"]

    # 4. Ask about physical forensic findings
    res4 = client.post("/chat/api/send", json={
        "session_uuid": session_uuid,
        "message": "Explain the forensic findings and ELA"
    })
    assert res4.status_code == 200
    data4 = res4.get_json()
    assert "2D-FFT" in data4["reply"]
    assert "Error Level Analysis" in data4["reply"]

    # 5. Ask about risk assessment
    res5 = client.post("/chat/api/send", json={
        "session_uuid": session_uuid,
        "message": "Explain my risk assessment score"
    })
    assert res5.status_code == 200
    data5 = res5.get_json()
    assert "82.0" in data5["reply"]
    assert "High Review Priority" in data5["reply"]

    # Verify message persistence in DB
    with app.app_context():
        messages = ChatMessage.query.filter_by(session_id=chat_session_id).all()
        assert len(messages) == 10  # 5 user prompts + 5 assistant responses

def test_chat_tenant_isolation(app, client):
    """Users cannot send messages to or manipulate other users' chat sessions"""
    with app.app_context():
        user_a = User(full_name="Alice User", email="alice@faceguard.ai", is_verified=True, role="user")
        user_a.set_password("SecurePass123!")
        user_b = User(full_name="Bob User", email="bob@faceguard.ai", is_verified=True, role="user")
        user_b.set_password("SecurePass123!")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        session_b = ChatSession(user_id=user_b.id, title="Bob Confidential")
        db.session.add(session_b)
        db.session.commit()
        session_b_uuid = session_b.session_uuid

    # Login as User A
    client.post("/auth/login", data={"email": "alice@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Attempt to post to Bob's session
    res_forbidden = client.post("/chat/api/send", json={
        "session_uuid": session_b_uuid,
        "message": "Attacking your session"
    })
    assert res_forbidden.status_code == 404
    data = res_forbidden.get_json()
    assert data["status"] == "error"

def test_chat_session_deletion(app, client):
    """Users can delete their own chat session which cascade deletes messages"""
    with app.app_context():
        user = User(full_name="Delete Me", email="delete@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        session = ChatSession(user_id=user.id, title="Temporary")
        db.session.add(session)
        db.session.commit()

        msg = ChatMessage(session_id=session.id, sender="user", content="Hello world")
        db.session.add(msg)
        db.session.commit()
        session_uuid = session.session_uuid

    client.post("/auth/login", data={"email": "delete@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_del = client.post(f"/chat/session/{session_uuid}/delete", follow_redirects=True)
    assert res_del.status_code == 200

    with app.app_context():
        assert ChatSession.query.filter_by(session_uuid=session_uuid).first() is None
        assert ChatMessage.query.filter_by(content="Hello world").first() is None
