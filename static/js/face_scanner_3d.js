/**
 * FACEGUARD AI - Advanced Holographic Face Scanner Controller
 * Module: static/js/face_scanner_3d.js
 * 
 * Powered by Cyber Holographic UI Subsystem:
 * - Controls the Ultra-Detailed 3D Biometric Holographic Face viewport (Photo 2)
 * - Sweeping cyber laser scan line with variable frequencies
 * - Real-time analysis status pulse (Scanning, Authentic, Deepfake)
 * - Interactive reset & examination trigger
 * - Full backward-compatible API for Overview AI scanner pipeline:
 *   â€¢ window.FaceScanner3D.startScan()
 *   â€¢ window.FaceScanner3D.setResult(isReal, confidence)
 *   â€¢ window.FaceScanner3D.reset()
 */

(function () {
    "use strict";

    class HolographicFaceScannerController {
        constructor() {
            this.card = document.getElementById("faceScannerCard");
            this.img = document.getElementById("holographicFaceRenderImg");
            this.laser = document.getElementById("holographicLaserLine");
            this.beacon = document.getElementById("scannerBeacon");
            this.badge = document.getElementById("scannerBadge");
            this.resetBtn = document.getElementById("resetFaceViewBtn");

            this.state = "idle";
            this.init();
        }

        init() {
            if (this.resetBtn) {
                this.resetBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    this.reset();
                });
            }

            if (this.card) {
                this.card.addEventListener("click", () => {
                    this.pulse();
                });
            }
        }

        pulse() {
            if (!this.img) return;
            this.img.style.filter = "drop-shadow(0 0 25px rgba(0, 240, 255, 0.9)) brightness(1.15)";
            setTimeout(() => {
                if (this.img && this.state === "idle") {
                    this.img.style.filter = "";
                }
            }, 600);
        }

        startScan() {
            this.state = "scanning";
            if (this.laser) {
                this.laser.style.animationDuration = "0.9s";
                this.laser.style.boxShadow = "0 0 24px #00f0ff, 0 0 45px rgba(0, 240, 255, 0.95)";
            }
            if (this.img) {
                this.img.style.filter = "drop-shadow(0 0 25px rgba(0, 240, 255, 0.75)) brightness(1.15)";
            }
            if (this.badge) {
                this.badge.innerHTML = '<i class="bi bi-arrow-repeat spin me-1"></i>ANALYZING BIOMETRICS...';
                this.badge.className = "badge bg-primary bg-opacity-75 text-white border border-info font-mono small px-2 py-1 shadow-sm";
            }
            if (this.beacon) {
                this.beacon.className = "pulse-beacon beacon-cyan";
            }
        }

        setResult(isReal, confidence) {
            this.state = isReal ? "real" : "fake";
            const confVal = typeof confidence === "number" ? confidence.toFixed(1) : parseFloat(confidence || 0).toFixed(1);

            if (this.laser) {
                this.laser.style.animationDuration = "2.6s";
                if (isReal) {
                    this.laser.style.background = "linear-gradient(90deg, transparent 0%, #10b981 50%, transparent 100%)";
                    this.laser.style.boxShadow = "0 0 18px #10b981, 0 0 36px rgba(16, 185, 129, 0.7)";
                } else {
                    this.laser.style.background = "linear-gradient(90deg, transparent 0%, #f43f5e 50%, transparent 100%)";
                    this.laser.style.boxShadow = "0 0 18px #f43f5e, 0 0 36px rgba(244, 63, 94, 0.8)";
                }
            }

            if (this.img) {
                if (isReal) {
                    this.img.style.filter = "drop-shadow(0 0 24px rgba(16, 185, 129, 0.55)) brightness(1.05)";
                } else {
                    this.img.style.filter = "drop-shadow(0 0 24px rgba(244, 63, 94, 0.65)) brightness(1.05)";
                }
            }

            if (this.card) {
                this.card.style.borderColor = isReal ? "rgba(16, 185, 129, 0.7)" : "rgba(244, 63, 94, 0.7)";
                this.card.style.boxShadow = isReal ? "0 0 32px rgba(16, 185, 129, 0.25)" : "0 0 32px rgba(244, 63, 94, 0.25)";
            }

            if (this.beacon) {
                this.beacon.className = isReal ? "pulse-beacon beacon-green" : "pulse-beacon beacon-rose";
            }

            if (this.badge) {
                if (isReal) {
                    this.badge.innerHTML = `<i class="bi bi-shield-check me-1"></i>AUTHENTIC (${confVal}%)`;
                    this.badge.className = "badge bg-success bg-opacity-75 text-white border border-success font-mono small px-2 py-1 shadow-sm";
                } else {
                    this.badge.innerHTML = `<i class="bi bi-shield-x me-1"></i>DEEPFAKE DETECTED (${confVal}%)`;
                    this.badge.className = "badge bg-danger bg-opacity-75 text-white border border-danger font-mono small px-2 py-1 shadow-sm";
                }
            }
        }

        reset() {
            this.state = "idle";
            if (this.laser) {
                this.laser.style.animationDuration = "3.5s";
                this.laser.style.background = "";
                this.laser.style.boxShadow = "";
            }
            if (this.img) {
                this.img.style.filter = "";
            }
            if (this.card) {
                this.card.style.borderColor = "";
                this.card.style.boxShadow = "";
            }
            if (this.beacon) {
                this.beacon.className = "pulse-beacon beacon-cyan";
            }
            if (this.badge) {
                this.badge.innerHTML = '<i class="bi bi-shield-check me-1"></i>SYSTEM ONLINE';
                this.badge.className = "badge bg-dark bg-opacity-75 text-info border border-info border-opacity-50 font-mono small px-2 py-1 shadow-sm";
            }
        }
    }

    // Initialize once DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            window.FaceScanner3D = new HolographicFaceScannerController();
        });
    } else {
        window.FaceScanner3D = new HolographicFaceScannerController();
    }
})();
