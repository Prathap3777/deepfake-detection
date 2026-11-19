"""
FACEGUARD AI - Batch Image Processing Pipeline
Module: faceguard/core/batch.py
"""
import os
import gc
import uuid
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from faceguard.extensions import db
from faceguard.models.batch import BatchJob, BatchItem
from faceguard.models.scan import Scan, FaceResult
from faceguard.core.detector import get_predictor
from faceguard.core.risk import compute_risk_assessment

def process_batch_upload(user_id, file_list, upload_folder, batch_title="Batch Investigation"):
    """
    Processes a collection of uploaded images memory-safely.
    Creates BatchJob and BatchItem records, as well as individual Scan records.
    """
    batch = BatchJob(
        user_id=user_id,
        title=batch_title,
        total_files=len(file_list),
        status="processing"
    )
    db.session.add(batch)
    db.session.flush()

    predictor = get_predictor()
    real_count = 0
    fake_count = 0
    failed_count = 0

    for file in file_list:
        if not file or not file.filename.strip():
            continue

        orig_filename = secure_filename(file.filename) or "batch_item.jpg"
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
        item_uuid = uuid.uuid4().hex[:12]
        saved_filename = f"batch_{item_uuid}.{ext}"
        saved_path = os.path.join(upload_folder, saved_filename)

        try:
            file.save(saved_path)

            pred_res = predictor.predict(saved_path, mode="standard", save_artifacts=True)
            forensics = pred_res.get("forensics", {})

            risk_info = compute_risk_assessment(
                cnn_prediction=pred_res.get("prediction", "REAL"),
                cnn_confidence=pred_res.get("confidence", 0.0),
                sensor_variance=forensics.get("sensor_noise_variance", 50.0) or 50.0,
                fft_ratio=forensics.get("frequency_fft_ratio", 0.72) or 0.72,
                ela_uniformity=forensics.get("ela_uniformity", 1.2) or 1.2,
                chroma_score=forensics.get("chromatic_coherence", 0.88) or 0.88,
                has_exif=False,
                face_count=pred_res.get("face_count", 0)
            )

            is_fake = (pred_res.get("prediction") == "FAKE")
            if is_fake:
                fake_count += 1
            else:
                real_count += 1

            # Create individual Scan record for history and analytics
            scan = Scan(
                scan_uuid=str(uuid.uuid4()),
                user_id=user_id,
                media_type="image",
                original_filename=orig_filename,
                saved_filename=saved_filename,
                face_count=pred_res.get("face_count", 0),
                overall_prediction=pred_res.get("prediction"),
                overall_confidence=pred_res.get("confidence", 0.0),
                risk_score=risk_info["risk_score"],
                review_priority=risk_info["review_priority"],
                annotated_path=pred_res.get("annotated_image_path"),
                status="completed"
            )
            db.session.add(scan)
            db.session.flush()

            # Create BatchItem record
            item = BatchItem(
                batch_id=batch.id,
                scan_id=scan.id,
                original_filename=orig_filename,
                saved_filename=saved_filename,
                face_count=pred_res.get("face_count", 0),
                prediction=pred_res.get("prediction"),
                confidence=pred_res.get("confidence", 0.0),
                risk_score=risk_info["risk_score"],
                review_priority=risk_info["review_priority"],
                status="completed",
                thumbnail_path=pred_res.get("annotated_image_path") or f"static/uploads/{saved_filename}"
            )
            db.session.add(item)

        except Exception as e:
            failed_count += 1
            item = BatchItem(
                batch_id=batch.id,
                original_filename=orig_filename,
                saved_filename=saved_filename if os.path.exists(saved_path) else "",
                prediction="ERROR",
                status="failed",
                error_message=str(e)
            )
            db.session.add(item)

        finally:
            batch.processed_files += 1
            gc.collect()

    # Update Batch Aggregates
    batch.real_count = real_count
    batch.fake_count = fake_count
    batch.failed_count = failed_count
    total_valid = real_count + fake_count
    batch.threat_rate = round((fake_count / total_valid * 100.0), 1) if total_valid > 0 else 0.0
    batch.status = "completed"
    batch.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    return batch
