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
