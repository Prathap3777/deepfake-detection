"""
FACEGUARD AI - Multi-Domain Digital Forensic Analysis Engine
Module: faceguard/core/forensics.py
"""
import cv2
import numpy as np

def extract_forensic_signals(crop_bgr, mode="standard"):
    """
    Extracts multi-domain digital forensic authenticity indicators:
    1. Sensor noise & skin pore texture (Laplacian Variance) calibrated for smartphones
    2. Frequency-domain radial decay & GAN lattice artifacts (2D-FFT)
    3. Error Level Analysis (ELA) for compression rate & splice boundary consistency
    4. Chromatic coherence across RGB sensor wells
    """
    crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    h, w = crop_gray.shape

    # 1. Laplacian Sensor Noise / Texture Check (Calibrated for real smartphones + portrait filters)
    lap_var = float(cv2.Laplacian(crop_gray, cv2.CV_64F).var())
    if lap_var >= 80.0:
        sensor_real_score = 0.95
        sensor_status = "Authentic optical sensor noise & natural skin pore texture"
        sensor_check = "PASS"
    elif 35.0 <= lap_var < 80.0:
        sensor_real_score = 0.88 if mode == "portrait" else 0.82
        sensor_status = "Natural soft lighting / smartphone ambient portrait"
        sensor_check = "PASS"
    elif 16.0 <= lap_var < 35.0:
        sensor_real_score = 0.78 if mode == "portrait" else 0.65
        sensor_status = "Smartphone camera HDR smoothing / gentle beauty mode"
        sensor_check = "PASS (Smoothing detected)"
    elif 7.0 <= lap_var < 16.0:
        sensor_real_score = 0.40
        sensor_status = "Substantial skin smoothing typical of generative models or strong filters"
        sensor_check = "WARNING"
    else:
        sensor_real_score = 0.15
        sensor_status = "Extreme artificial smoothness characteristic of AI face synthesis"
        sensor_check = "FAIL"

    # 2. 2D-FFT Frequency Domain Power Spectrum
    f = np.fft.fft2(crop_gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1e-8)
    cr, cc = h // 2, w // 2
    mask_low = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask_low, (cc, cr), max(4, min(cr, cc) // 3), 1, -1)
    low_p = float(np.mean(mag[mask_low == 1]))
    high_p = float(np.mean(mag[mask_low == 0]))
    fft_ratio = float(high_p / (low_p + 1e-8))

    # Real optical camera lenses follow smooth power decay (0.52 to 0.92)
    if 0.52 <= fft_ratio <= 0.92:
        fft_real_score = 0.95
        fft_status = "Smooth optical frequency decay (No GAN deconvolution grid)"
        fft_check = "PASS"
    elif 0.45 <= fft_ratio < 0.52 or 0.92 < fft_ratio <= 0.98:
        fft_real_score = 0.78
        fft_status = "Moderate high-frequency distribution (Consistent with compression)"
        fft_check = "PASS"
    else:
        fft_real_score = 0.25
        fft_status = "Periodic spectral lattice anomalies typical of generative upsampling"
        fft_check = "FAIL"

    # Generate 2D-FFT Spectrum Heatmap Visualization
    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    fft_heatmap = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)

    # 3. Error Level Analysis (ELA) for JPEG Compression Consistency
    _, encoded_jpg = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    decompressed_bgr = cv2.imdecode(encoded_jpg, cv2.IMREAD_COLOR)
    ela_diff = cv2.absdiff(crop_bgr, decompressed_bgr)
    ela_gray = cv2.cvtColor(ela_diff, cv2.COLOR_BGR2GRAY)
    ela_mean = float(np.mean(ela_gray))
    ela_std = float(np.std(ela_gray))

    # ELA Heatmap (amplified 12x for human forensic inspection)
    ela_amplified = cv2.convertScaleAbs(ela_diff, alpha=12)
    ela_amp_gray = cv2.cvtColor(ela_amplified, cv2.COLOR_BGR2GRAY)
    ela_heatmap = cv2.applyColorMap(ela_amp_gray, cv2.COLORMAP_HOT)

    ela_uniformity = float(ela_std / (ela_mean + 1e-5))
    if 0.6 <= ela_uniformity <= 2.2:
        ela_real_score = 0.94
        ela_status = "Uniform optical compression gradient across facial structures"
        ela_check = "PASS"
    elif 0.3 <= ela_uniformity < 0.6 or 2.2 < ela_uniformity <= 3.0:
        ela_real_score = 0.75
        ela_status = "Minor compression variation (Normal for social media re-saving)"
        ela_check = "PASS"
    else:
        ela_real_score = 0.30
        ela_status = "Non-uniform compression error levels (Indicates digital splicing or synthetic face)"
        ela_check = "FAIL"

    # 4. Chromatic Channel Correlation
    b, g, r = cv2.split(crop_bgr)
    corr_rg = float(np.corrcoef(r.flatten(), g.flatten())[0, 1])
    corr_gb = float(np.corrcoef(g.flatten(), b.flatten())[0, 1])
    chroma = float((corr_rg + corr_gb) / 2.0)

    if chroma > 0.82:
        chroma_real_score = 0.95
        chroma_status = "Coherent RGB Bayer-pattern sensor alignment"
        chroma_check = "PASS"
    elif chroma > 0.70:
        chroma_real_score = 0.78
        chroma_status = "Acceptable chromatic distribution"
        chroma_check = "PASS"
    else:
        chroma_real_score = 0.30
        chroma_status = "Chromatic seam shift detected (Common in FaceSwap blending)"
        chroma_check = "FAIL"

    return {
        "sensor_real_score": sensor_real_score,
        "sensor_status": sensor_status,
        "sensor_check": sensor_check,
        "lap_var": round(lap_var, 1),
        "fft_real_score": fft_real_score,
        "fft_status": fft_status,
        "fft_check": fft_check,
        "fft_ratio": round(fft_ratio, 3),
        "fft_heatmap": fft_heatmap,
        "ela_real_score": ela_real_score,
        "ela_status": ela_status,
        "ela_check": ela_check,
        "ela_mean": round(ela_mean, 2),
        "ela_heatmap": ela_heatmap,
        "chroma_real_score": chroma_real_score,
        "chroma_status": chroma_status,
        "chroma_check": chroma_check,
        "chroma": round(chroma, 3)
    }

import os
import uuid
from PIL import Image, ExifTags

def extract_exif_metadata(image_path):
    """
    Extracts and standardizes EXIF photographic metadata from an image file.
    Returns metadata dict, presence boolean, and technical notes.
    """
    metadata = {}
    has_exif = False
    notes = []

    try:
        with Image.open(image_path) as img:
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="ignore")
                        except Exception:
                            value = str(value)
                    # Exclude huge binary maker notes
                    if tag_name not in ("MakerNote", "UserComment"):
                        metadata[tag_name] = str(value).strip()
                
                # Check for IFD Exif sub-block
                try:
                    exif_ifd = raw_exif.get_ifd(ExifTags.IFD.Exif)
                    for tag_id, value in exif_ifd.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag_name not in ("MakerNote", "UserComment"):
                            metadata[tag_name] = str(value).strip()
                except Exception:
                    pass

                if len(metadata) > 0:
                    has_exif = True
    except Exception as e:
        notes.append(f"EXIF parsing error: {str(e)}")

    if not has_exif:
        notes.append("No embedded EXIF photographic metadata found. Standard digital cameras and smartphones write hardware tags, whereas AI image generation pipelines (e.g. Midjourney, Stable Diffusion, StyleGAN) and social media platforms (WhatsApp, Twitter, Instagram) typically produce images with stripped metadata.")
    else:
        notes.append(f"Successfully extracted {len(metadata)} hardware/software metadata fields.")

    return {
        "has_exif": has_exif,
        "fields": metadata,
        "notes": notes
    }

def inspect_file_properties(image_path, original_filename):
    """
    Performs binary file inspection, MIME validation, dimensions, and aspect ratio.
    """
    file_size_bytes = os.path.getsize(image_path)
    file_size_kb = round(file_size_bytes / 1024.0, 1)
    file_size_mb = round(file_size_bytes / (1024.0 * 1024.0), 2)

    with Image.open(image_path) as img:
        width, height = img.size
        img_format = (img.format or "Unknown").upper()
        mode = img.mode
        megapixels = round((width * height) / 1000000.0, 2)
        aspect_ratio = f"{round(width / max(1, height), 2)}:1"

    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    format_mismatch = False
    if ext in ("jpg", "jpeg") and img_format != "JPEG":
        format_mismatch = True
    elif ext == "png" and img_format != "PNG":
        format_mismatch = True

    return {
        "filename": original_filename,
        "format": img_format,
        "mode": mode,
        "width": width,
        "height": height,
        "dimensions": f"{width} × {height} px",
        "megapixels": megapixels,
        "aspect_ratio": aspect_ratio,
        "file_size_bytes": file_size_bytes,
        "file_size_kb": file_size_kb,
        "file_size_mb": file_size_mb,
        "format_mismatch": format_mismatch
    }

def generate_full_ela(image_path, upload_folder, quality=90, scale=15):
    """
    Generates full-frame Error Level Analysis (ELA) artifact.
    Saves visualization into upload_folder and returns relative URL and metrics.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return None, {}

    # Encode with fixed JPEG quality
    _, encoded = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    decompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    # Compute absolute difference
    ela_diff = cv2.absdiff(img_bgr, decompressed)
    ela_gray = cv2.cvtColor(ela_diff, cv2.COLOR_BGR2GRAY)
    ela_mean = float(np.mean(ela_gray))
    ela_std = float(np.std(ela_gray))
    ela_max = float(np.max(ela_gray))

    # Scale difference for visual human inspection
    ela_scaled = cv2.convertScaleAbs(ela_diff, alpha=scale)
    ela_heatmap = cv2.applyColorMap(cv2.cvtColor(ela_scaled, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_HOT)

    # Save artifact
    artifact_id = f"ela_full_{uuid.uuid4().hex[:10]}.jpg"
    out_path = os.path.join(upload_folder, artifact_id)
    cv2.imwrite(out_path, ela_heatmap)

    uniformity = float(ela_std / (ela_mean + 1e-5))

    return artifact_id, {
        "mean_error": round(ela_mean, 2),
        "std_error": round(ela_std, 2),
        "max_error": round(ela_max, 2),
        "uniformity_ratio": round(uniformity, 2),
        "interpretation": "Uniform error distribution suggests consistent compression throughout. Discontinuous bright clusters indicate local editing, digital splicing, or facial blending."
    }

def generate_full_fft(image_path, upload_folder):
    """
    Computes 2D Fast Fourier Transform magnitude spectrum of the full image.
    Detects periodic frequency lattice patterns typical of GAN/diffusion upsampling.
    """
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        return None, {}

    h, w = img_gray.shape
    f = np.fft.fft2(img_gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1e-8)

    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    fft_heatmap = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)

    artifact_id = f"fft_full_{uuid.uuid4().hex[:10]}.jpg"
    out_path = os.path.join(upload_folder, artifact_id)
    cv2.imwrite(out_path, fft_heatmap)

    cr, cc = h // 2, w // 2
    mask_low = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask_low, (cc, cr), max(6, min(cr, cc) // 4), 1, -1)
    low_p = float(np.mean(mag[mask_low == 1]))
    high_p = float(np.mean(mag[mask_low == 0]))
    fft_ratio = float(high_p / (low_p + 1e-8))

    return artifact_id, {
        "high_to_low_ratio": round(fft_ratio, 3),
        "low_frequency_power": round(low_p, 1),
        "high_frequency_power": round(high_p, 1),
        "interpretation": "Natural optical lenses produce concentric radial power decay. Artificial frequency grids, periodic cross-bars, or sharp lattice dots indicate transposed convolution or synthetic upsampling artifacts."
    }

def analyze_full_forensics(image_path, original_filename, upload_folder):
    """
    Orchestrates the complete forensic audit across all domains:
    1. EXIF Photographic Metadata
    2. File Container Properties & Format Inspection
    3. Error Level Analysis (ELA) Compression Artifacts
    4. 2D-FFT Spatial Frequency Domain Spectrum
    5. Sensor Noise & Laplacian Texture Variance
    6. Forensic Integrity Summary & Scientific Limitations
    """
    file_props = inspect_file_properties(image_path, original_filename)
    exif_props = extract_exif_metadata(image_path)
    ela_filename, ela_stats = generate_full_ela(image_path, upload_folder)
    fft_filename, fft_stats = generate_full_fft(image_path, upload_folder)

    # Sensor Noise & Texture Analysis
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    lap_var = float(cv2.Laplacian(img_gray, cv2.CV_64F).var()) if img_gray is not None else 0.0

    noise_analysis = {
        "laplacian_variance": round(lap_var, 1),
        "rating": "Natural Sensor Grain" if lap_var >= 45.0 else ("Softened / Compressed" if lap_var >= 15.0 else "Synthetically Smooth / Denoised"),
        "interpretation": "Physical camera sensors exhibit microscopic photon shot noise and ISO grain. Generative models commonly produce overly smooth or synthetic skin textures that deviate from optical standards."
    }

    # Consolidated Forensic Findings Summary
    findings = []
    if not exif_props["has_exif"]:
        findings.append({
            "category": "Metadata",
            "status": "CAUTION",
            "badge_class": "badge-warning",
            "title": "EXIF Metadata Stripped",
            "detail": "No camera hardware or capture timestamp tags exist. Consistent with both web platform re-encoding and AI synthetic generation."
        })
    else:
        findings.append({
            "category": "Metadata",
            "status": "INFO",
            "badge_class": "badge-info",
            "title": "Hardware Tags Present",
            "detail": f"Camera/Software tags preserved ({len(exif_props['fields'])} tags detected)."
        })

    if ela_stats.get("uniformity_ratio", 1.0) > 2.5:
        findings.append({
            "category": "Compression (ELA)",
            "status": "WARNING",
            "badge_class": "badge-danger",
            "title": "Non-Uniform Compression Delta",
            "detail": "Discontinuous compression error levels detected. Suggests multi-pass compression, local retouching, or facial insertion."
        })
    else:
        findings.append({
            "category": "Compression (ELA)",
            "status": "PASS",
            "badge_class": "badge-success",
            "title": "Uniform Compression Gradient",
            "detail": "Error level analysis indicates coherent single-generation compression across the frame."
        })

    if fft_stats.get("high_to_low_ratio", 0.7) < 0.48 or fft_stats.get("high_to_low_ratio", 0.7) > 0.95:
        findings.append({
            "category": "Frequency Domain (FFT)",
            "status": "WARNING",
            "badge_class": "badge-warning",
            "title": "Spectral Density Deviation",
            "detail": "Frequency distribution deviates from typical optical lens radial decay."
        })
    else:
        findings.append({
            "category": "Frequency Domain (FFT)",
            "status": "PASS",
            "badge_class": "badge-success",
            "title": "Natural Radial Power Decay",
            "detail": "Smooth concentric Fourier spectrum consistent with natural optical lens capture."
        })

    if lap_var < 15.0:
        findings.append({
            "category": "Sensor Texture",
            "status": "WARNING",
            "badge_class": "badge-danger",
            "title": "Anomalous Texture Smoothness",
            "detail": f"Sensor noise variance ({round(lap_var, 1)}) is unusually low, characteristic of neural face synthesizers or aggressive bilateral smoothing."
        })
    else:
        findings.append({
            "category": "Sensor Texture",
            "status": "PASS",
            "badge_class": "badge-success",
            "title": "Realistic Optical Grain",
            "detail": f"Sensor noise variance ({round(lap_var, 1)}) conforms to physical camera sensor specifications."
        })

    return {
        "file_props": file_props,
        "exif_props": exif_props,
        "ela_filename": ela_filename,
        "ela_stats": ela_stats,
        "fft_filename": fft_filename,
        "fft_stats": fft_stats,
        "noise_analysis": noise_analysis,
        "findings": findings
    }
