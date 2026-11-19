"""
FACEGUARD AI - Batch Image Intelligence Test Suite
Module: tests/test_batch_intelligence.py
"""
import io
import os
import pytest
import numpy as np
import cv2
from faceguard import create_app
from faceguard.config import TestingConfig
from faceguard.extensions import db
from faceguard.models.user import User
from faceguard.models.batch import BatchJob, BatchItem

@pytest.fixture
def app(tmp_path):
    app = create_app(TestingConfig)
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def batch_image_samples(tmp_path):
    """Creates a trio of synthetic test images for batch processing"""
    paths = []
    for i in range(3):
        p = str(tmp_path / f"batch_sample_{i}.jpg")
        img = np.zeros((160, 160, 3), dtype=np.uint8)
        cv2.circle(img, (80, 80), 45, (200, 175, 140), -1)
        noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
        cv2.imwrite(p, img)
        paths.append(p)
    return paths

def test_batch_page_requires_login(client):
    """Anonymous visitors are redirected to login"""
    res = client.get("/detect/batch")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_batch_page_renders_for_logged_in_user(app, client):
    """Authenticated users can view batch workspace"""
    with app.app_context():
        user = User(full_name="Batch Lead", email="batch@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "batch@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/batch")
    assert res.status_code == 200
    assert b"Batch Image Intelligence" in res.data
    assert b"Investigation Session Title" in res.data

def test_batch_rejects_empty_submission(app, client):
    """Empty batch submission triggers warning"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.post("/detect/batch", data={}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please choose at least one image file" in res.data

def test_batch_enforces_max_files_limit(app, client):
    """Rejects batches exceeding configured maximum limit (>20 files)"""
    with app.app_context():
        user = User(full_name="Tester", email="test@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "test@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    # Prepare 22 fake file uploads
    files = [
        (io.BytesIO(b"fake image data"), f"img_{i}.jpg")
        for i in range(22)
    ]
    res = client.post("/detect/batch", data={"images": files}, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert b"Batch limit exceeded" in res.data

def test_batch_processing_execution_end_to_end(app, client, batch_image_samples):
    """Submits multi-image batch, processes queue, and verifies KPI widgets and items table"""
    with app.app_context():
        user = User(full_name="Queue Operator", email="op@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"email": "op@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)

    file_uploads = []
    for p in batch_image_samples:
        with open(p, "rb") as f:
            file_uploads.append((io.BytesIO(f.read()), os.path.basename(p)))

    res = client.post(
        "/detect/batch",
        data={
            "title": "Alpha Evidence Batch",
            "images": file_uploads
        },
        content_type="multipart/form-data",
        follow_redirects=True
    )

    assert res.status_code == 200
    assert b"Alpha Evidence Batch" in res.data
    assert b"Batch Execution Complete" in res.data
    assert b"Batch Threat Index" in res.data
    assert b"Download Combined PDF Report" in res.data

    with app.app_context():
        job = BatchJob.query.filter_by(title="Alpha Evidence Batch").first()
        assert job is not None
        assert job.total_files == 3
        assert job.processed_files == 3
        assert len(job.items) == 3

def test_batch_combined_pdf_report_export(app, client, batch_image_samples):
    """Generates and downloads combined batch PDF dossier"""
    with app.app_context():
        user = User(full_name="PDF Specialist", email="pdfspec@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        # Create batch job with 2 items
        job = BatchJob(
            user_id=user.id,
            batch_uuid="batch-pdf-uuid-123",
            title="Dossier Test Batch",
            total_files=2,
            processed_files=2,
            real_count=2,
            fake_count=0,
            threat_rate=0.0,
            status="completed"
        )
        db.session.add(job)
        db.session.flush()

        item1 = BatchItem(batch_id=job.id, original_filename="photo_01.jpg", saved_filename="s1.jpg", face_count=1, prediction="REAL", confidence=94.5, review_priority="Lower Review Priority")
        item2 = BatchItem(batch_id=job.id, original_filename="photo_02.jpg", saved_filename="s2.jpg", face_count=1, prediction="REAL", confidence=92.0, review_priority="Lower Review Priority")
        db.session.add_all([item1, item2])
        db.session.commit()

    client.post("/auth/login", data={"email": "pdfspec@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    res = client.get("/detect/batch/batch-pdf-uuid-123/report")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert "batch_report_" in res.headers["Content-Disposition"]

def test_batch_status_api_polling(app, client):
    """Verifies REST API JSON status endpoint for background polling"""
    with app.app_context():
        user = User(full_name="API Poller", email="poll@faceguard.ai", is_verified=True)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        job = BatchJob(
            user_id=user.id,
            batch_uuid="batch-poll-uuid-456",
            title="Async Polling Job",
            total_files=5,
            processed_files=3,
            real_count=2,
            fake_count=1,
            threat_rate=33.3,
            status="processing"
        )
        db.session.add(job)
        db.session.commit()

    client.post("/auth/login", data={"email": "poll@faceguard.ai", "password": "SecurePass123!"}, follow_redirects=True)
    api_res = client.get("/detect/batch/api/status/batch-poll-uuid-456")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert data["success"] is True
    assert data["batch_uuid"] == "batch-poll-uuid-456"
    assert data["total_files"] == 5
    assert data["processed_files"] == 3
    assert data["threat_rate"] == 33.3
    assert data["status"] == "processing"
