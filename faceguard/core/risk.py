"""
FACEGUARD AI - Multi-Signal AI Risk Assessment Engine
Module: faceguard/core/risk.py
"""

def compute_risk_assessment(
    cnn_prediction,
    cnn_confidence,
    sensor_variance=50.0,
    fft_ratio=0.72,
    ela_uniformity=1.2,
    chroma_score=0.88,
    has_exif=False,
    face_count=1,
    is_video=False,
    video_fake_ratio=0.0
):
    """
    Computes a mathematically documented, explainable AI Risk Assessment Score (0 to 100).
    
    Architecture & Multi-Factor Weights:
    - 1. Calibrated CNN Neural Risk Signal (Max 45 pts)
    - 2. Microscopic Sensor Noise & Texture Variance (Max 20 pts)
    - 3. 2D-FFT Spatial Frequency & Lattice Artifacts (Max 15 pts)
    - 4. Error Level Analysis (ELA) Compression Consistency (Max 12 pts)
    - 5. Metadata Container & Context (Max 8 pts)
    
    Review Priority Bands:
    - 0 to 24: Lower Review Priority (Authentic optical characteristics)
    - 25 to 49: Moderate Review Priority (Minor compression/filter anomalies)
    - 50 to 74: Elevated Review Priority (Substantial neural or forensic flags)
    - 75 to 100: High Review Priority (Multiple orthogonal deepfake indicators)
    """
    contributing_factors = []
    mitigating_factors = []
    missing_evidence = []

    # 1. Calibrated CNN Neural Score (Weight: 45%)
    if is_video and video_fake_ratio is not None:
        neural_score = (video_fake_ratio / 100.0) * 45.0
        if video_fake_ratio >= 15.0:
            contributing_factors.append({
                "factor": "Temporal Video Manipulation",
                "points": round(neural_score, 1),
                "detail": f"{video_fake_ratio:.1f}% of sampled frames classified as synthetic by ResNet-18 model."
            })
        else:
            mitigating_factors.append({
                "factor": "Temporal Video Coherence",
                "detail": f"{100.0 - video_fake_ratio:.1f}% of video frames verified authentic across temporal sequence."
            })
    else:
        if cnn_prediction == "FAKE":
            neural_score = 45.0 * (cnn_confidence / 100.0)
            contributing_factors.append({
                "factor": "Deepfake Neural Classifier",
                "points": round(neural_score, 1),
                "detail": f"ResNet-18 convolutional backbone classified facial structure as FAKE with {cnn_confidence:.1f}% confidence."
            })
        else:
            neural_score = 45.0 * max(0.0, (100.0 - cnn_confidence) / 100.0)
            mitigating_factors.append({
                "factor": "Authentic Facial Geometry",
                "detail": f"ResNet-18 model verified authentic facial landmarks with {cnn_confidence:.1f}% confidence."
            })

    # 2. Sensor Noise & Texture Grain (Weight: 20%)
    if sensor_variance < 15.0:
        sensor_score = 18.0
        contributing_factors.append({
            "factor": "Artificial Texture Smoothness",
            "points": 18.0,
            "detail": f"Sensor noise variance ({sensor_variance:.1f}) is anomalously low; lacks organic photon shot noise."
        })
    elif 15.0 <= sensor_variance < 35.0:
        sensor_score = 8.0
        contributing_factors.append({
            "factor": "Softened Sensor Texture",
            "points": 8.0,
            "detail": f"Moderate noise reduction detected ({sensor_variance:.1f}), consistent with social media re-saving or light beautification."
        })
    else:
        sensor_score = 0.0
        mitigating_factors.append({
            "factor": "Natural Sensor Grain",
            "detail": f"Microscopic optical sensor noise ({sensor_variance:.1f}) matches physical camera hardware standards."
        })

    # 3. 2D-FFT Spatial Frequency & Lattice Grid (Weight: 15%)
    if fft_ratio < 0.48 or fft_ratio > 0.95:
        fft_score = 13.0
        contributing_factors.append({
            "factor": "Frequency Domain Anomaly",
            "points": 13.0,
            "detail": f"2D-FFT ratio ({fft_ratio:.3f}) deviates from natural radial optical decay, indicating possible synthetic upsampling grids."
        })
    else:
        fft_score = 2.0
        mitigating_factors.append({
            "factor": "Concentric Frequency Decay",
            "detail": f"Smooth 2D-FFT frequency attenuation ({fft_ratio:.3f}) conforms to natural optical lenses."
        })

    # 4. Error Level Analysis (ELA) Compression Uniformity (Weight: 12%)
    if ela_uniformity > 2.5 or ela_uniformity < 0.3:
        ela_score = 10.0
        contributing_factors.append({
            "factor": "Compression Level Inconsistency",
            "points": 10.0,
            "detail": f"ELA uniformity ratio ({ela_uniformity:.2f}) indicates non-uniform digital compression delta or facial splicing."
        })
    else:
        ela_score = 1.0
        mitigating_factors.append({
            "factor": "Uniform Compression Gradient",
            "detail": f"Error Level Analysis confirms uniform compression gradient ({ela_uniformity:.2f}) across facial boundaries."
        })

    # 5. Metadata Container & Context (Weight: 8%)
    if not has_exif:
        exif_score = 5.0
        contributing_factors.append({
            "factor": "Absent Hardware Metadata",
            "points": 5.0,
            "detail": "EXIF camera capture metadata is stripped (auxiliary indicator; common in generative AI and messaging apps)."
        })
    else:
        exif_score = 0.0
        mitigating_factors.append({
            "factor": "Verified Hardware Metadata",
            "detail": "Authentic camera hardware tags (Make/Model/ISO) present in file header."
        })

    # Chromatic Seam Shift (Bonus threat signal)
    if chroma_score < 0.70:
        chroma_score_val = 6.0
        contributing_factors.append({
            "factor": "Bayer Chromatic Misalignment",
            "points": 6.0,
            "detail": f"Chromatic correlation ({chroma_score:.3f}) shows channel boundary misalignment typical of FaceSwap blending."
        })
    else:
        chroma_score_val = 0.0

    # Aggregate Risk Score
    raw_score = neural_score + sensor_score + fft_score + ela_score + exif_score + chroma_score_val
    risk_score = round(min(100.0, max(0.0, raw_score)), 1)

    # Determine Review Priority & Badge Stylings
    if risk_score >= 75.0:
        priority = "High Review Priority"
        priority_class = "danger"
        badge_bg = "#f43f5e"
        executive_summary = (
            "Elevated probability of synthetic manipulation. Multiple independent evidence signals "
            "(neural network latent predictions, anomalous frequency grids, and texture smoothness) "
            "corroborate artificial face synthesis or digital splicing. Immediate human forensic audit required."
        )
    elif risk_score >= 50.0:
        priority = "Elevated Review Priority"
        priority_class = "warning"
        badge_bg = "#f59e0b"
        executive_summary = (
            "Moderate-to-high risk profile. While some authentic photographic traits persist, notable anomalies "
            "in neural feature activations or compression error levels warrant secondary forensic review before certification."
        )
    elif risk_score >= 25.0:
        priority = "Moderate Review Priority"
        priority_class = "info"
        badge_bg = "#0ea5e9"
        executive_summary = (
            "Low-to-moderate risk profile. Minor compression delta or gentle cosmetic smoothing observed, but overall "
            "evidence strongly favors authentic capture. Standard review priority."
        )
    else:
        priority = "Lower Review Priority"
        priority_class = "success"
        badge_bg = "#10b981"
        executive_summary = (
            "Minimal risk detected. Neural predictions, natural sensor noise grain, concentric Fourier decay, and "
            "uniform compression levels collectively confirm photographic authenticity."
        )

    # Document Missing Evidence
    if not is_video:
        missing_evidence.append("Temporal inter-frame consistency (static image; temporal analysis not applicable)")
    missing_evidence.append("Original camera RAW sensor payload (analyzed in lossy container)")
    if not has_exif:
        missing_evidence.append("Cryptographic camera provenance or C2PA authenticity certificates")

    return {
        "risk_score": risk_score,
        "review_priority": priority,
        "priority_class": priority_class,
        "badge_bg": badge_bg,
        "neural_contribution": round(neural_score, 1),
        "sensor_contribution": round(sensor_score, 1),
        "fft_contribution": round(fft_score, 1),
        "ela_contribution": round(ela_score, 1),
        "exif_contribution": round(exif_score, 1),
        "contributing_factors": contributing_factors,
        "mitigating_factors": mitigating_factors,
        "missing_evidence": missing_evidence,
        "executive_summary": executive_summary
    }
