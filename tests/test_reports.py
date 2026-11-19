"""
FACEGUARD AI - Forensic PDF Report Generation Test Suite
Module: tests/test_reports.py
"""
import os
import pytest
from faceguard import create_app
from faceguard.config import TestingConfig, BASE_DIR
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.scan import Scan, FaceResult
from faceguard.models.audit import PDFReport
from faceguard.utils.pdf import generate_scan_pdf

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

def test_reports_requires_login(client):
    """Anonymous visitors cannot access reports listing"""
    response = client.get("/reports/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

def test_reports_list_renders_empty_state_for_new_user(app, client):
    """New users see a clean empty state"""
    with app.app_context():
        user = User(full_name="Tom Reports", email="tom@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "tom@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/reports/")
    assert res.status_code == 200
    assert b"No Forensic PDF Dossiers Generated Yet" in res.data
    assert b"Browse Scan History" in res.data

def test_pdf_report_compilation_and_download_end_to_end(app, client):
    """Verifies that ReportLab compiles a valid PDF file and sends it with correct headers"""
    with app.app_context():
        user = User(full_name="Uma Scientist", email="uma@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="audit_portrait.jpg",
            saved_filename="audit_portrait_uuid.jpg",
            face_count=1,
            overall_prediction="REAL",
            overall_confidence=97.2,
            sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            analysis_mode="standard",
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()

        face = FaceResult(
            scan_id=scan.id,
            face_index=1,
            prediction="REAL",
            confidence=97.2,
            sensor_variance=62.4,
            fft_ratio=0.741,
            ela_mean=14.2,
            chroma_score=0.885
        )
        db.session.add(face)
        db.session.commit()

        # Direct compilation test
        pdf_record = generate_scan_pdf(scan)
        assert pdf_record is not None
        assert pdf_record.report_uuid is not None
        assert pdf_record.file_size_bytes > 0

        # Verify PDF magic bytes '%PDF' on disk
        cleaned_path = pdf_record.file_path.replace("static/", "").replace("static\\", "")
        abs_path = os.path.join(BASE_DIR, "static", cleaned_path)
        assert os.path.exists(abs_path)
        with open(abs_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF"

        report_uuid = pdf_record.report_uuid

    # Test download route
    client.post("/auth/login", data={"email": "uma@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_dl = client.get(f"/reports/{report_uuid}/download")
    assert res_dl.status_code == 200
    assert res_dl.headers["Content-Type"] == "application/pdf"
    assert "attachment" in res_dl.headers.get("Content-Disposition", "")
    assert res_dl.data.startswith(b"%PDF")

def test_generate_report_endpoint(app, client):
    """Tests the /reports/generate/<scan_uuid> launcher route"""
    with app.app_context():
        user = User(full_name="Victor Launcher", email="victor@faceguard.ai", is_verified=True, role="user")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        scan = Scan(
            user_id=user.id,
            media_type="image",
            original_filename="launch_test.jpg",
            saved_filename="launch_test_uuid.jpg",
            face_count=1,
            overall_prediction="FAKE",
            overall_confidence=91.5,
            status="completed"
        )
        db.session.add(scan)
        db.session.commit()
        scan_uuid = scan.scan_uuid

    client.post("/auth/login", data={"email": "victor@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_gen = client.get(f"/reports/generate/{scan_uuid}", follow_redirects=False)
    assert res_gen.status_code == 302
    assert "/reports/" in res_gen.headers["Location"]

def test_reports_tenant_isolation(app, client):
    """Users cannot download PDF reports belonging to other accounts"""
    with app.app_context():
        user_a = User(full_name="User A", email="usera@faceguard.ai", is_verified=True, role="user")
        user_a.set_password("SecurePass123!")
        user_b = User(full_name="User B", email="userb@faceguard.ai", is_verified=True, role="user")
        user_b.set_password("SecurePass123!")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        scan_b = Scan(
            user_id=user_b.id,
            media_type="image",
            original_filename="private_b.jpg",
            saved_filename="private_b.jpg",
            overall_prediction="REAL",
            status="completed"
        )
        db.session.add(scan_b)
        db.session.commit()

        pdf_b = generate_scan_pdf(scan_b)
        report_b_uuid = pdf_b.report_uuid

    # Login as User A
    client.post("/auth/login", data={"email": "usera@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res_forbidden = client.get(f"/reports/{report_b_uuid}/download")
    assert res_forbidden.status_code == 404
