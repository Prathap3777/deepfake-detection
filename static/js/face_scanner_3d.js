/**
 * FACEGUARD AI - Advanced 3D Holographic Face Scanner
 * Module: static/js/face_scanner_3d.js
 * Powered by Three.js (r128)
 * 
 * Phase 2 Upgrade:
 * - High-density parametric human facial anatomy (64x64 resolution, 8000+ faces)
 * - Sculpted forehead, brow ridge, orbital cavities, eyeballs, nose bridge, nostrils,
 *   philtrum, Cupid's bow, upper & lower lips, chin, jawline, ears, and neck column
 * - Ocular contour rings and bilateral ear auricles
 * - 68 Anatomical biometric landmark points mapped with sub-millimeter precision
 * - Volumetric inner luminescent holographic core + sparkling nodal matrix points
 * - Preserves laser scan sweep, rotating cyber platform, FPS telemetry, and Flask hooks
 */

(function () {
    "use strict";

    class HolographicFaceScanner {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            if (!this.container) return;

            this.scene = null;
            this.camera = null;
            this.renderer = null;
            this.clock = new THREE.Clock();

            // Mesh groups
            this.faceGroup = new THREE.Group();
            this.platformGroup = new THREE.Group();
            this.particles = null;

            // Interactive state
            this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
            this.isDragging = false;
            this.previousMousePosition = { x: 0, y: 0 };
            this.isScanning = false;
            this.scanState = "idle"; // 'idle' | 'scanning' | 'real' | 'fake'

            // Laser state
            this.laserY = 0;
            this.laserDirection = 1;
            this.laserSpeed = 1.2;

            // Telemetry elements
            this.rotEl = document.getElementById("faceRotX");
            this.fpsEl = document.getElementById("faceFps");
            this.frameCount = 0;
            this.lastFpsUpdate = 0;

            this.init();
        }

        init() {
            const width = this.container.clientWidth || 500;
            const height = this.container.clientHeight || 440;

            // 1. Scene
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(0x040711, 0.16);

            // 2. Camera
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            this.camera.position.set(0, 0, 4.3);

            // 3. Renderer
            this.renderer = new THREE.WebGLRenderer({
                antialias: true,
                alpha: true,
                powerPreference: "high-performance"
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.2;
            this.container.appendChild(this.renderer.domElement);

            // 4. Lights
            const ambientLight = new THREE.AmbientLight(0x00f0ff, 0.9);
            this.scene.add(ambientLight);

            const pointLight = new THREE.PointLight(0x00f0ff, 3.0, 12);
            pointLight.position.set(0, 1.8, 3.5);
            this.scene.add(pointLight);

            const rimLightCyan = new THREE.PointLight(0x00f0ff, 2.0, 8);
            rimLightCyan.position.set(2.5, 0.5, 1.5);
            this.scene.add(rimLightCyan);

            const rimLightPurple = new THREE.PointLight(0xa855f7, 2.2, 8);
            rimLightPurple.position.set(-2.5, -0.5, 1.5);
            this.scene.add(rimLightPurple);

            // 5. Build 3D Entities
            this.buildFacialMesh();
            this.buildEyeAndEarDetails();
            this.buildLandmarkPoints();
            this.buildLaserPlane();
            this.buildHolographicPlatform();
            this.buildParticleAura();

            this.scene.add(this.faceGroup);

            // 6. Bind Events
            this.bindEvents();

            // 7. Start Render Loop
            this.animate = this.animate.bind(this);
            requestAnimationFrame(this.animate);
        }

        /**
         * Sculpt High-Density Parametric Anatomical 3D Face Geometry (64x64 grid)
         */
        buildFacialMesh() {
            const widthSegments = 64;
            const heightSegments = 64;
            const radius = 1.0;
            const geometry = new THREE.SphereGeometry(radius, widthSegments, heightSegments);
            const pos = geometry.attributes.position;

            for (let i = 0; i < pos.count; i++) {
                let x = pos.getX(i);
                let y = pos.getY(i);
                let z = pos.getZ(i);

                // --- 1. Vertical Proportions: Head + Neck ---
                if (y > -0.2) {
                    y = 0.2 + (y - (-0.2)) * 0.95; // Cranium & upper facial dome
                } else {
                    y = 0.2 + (y - (-0.2)) * 1.45; // Lower jaw & descending cervical neck
                }

                // Cranial lateral width ratio
                x *= 0.88;
                z *= 1.05;

                // --- 2. Frontal Facial Features Sculpting (z > -0.2) ---
                if (z > -0.2) {
                    // Forehead curvature & Supraorbital brow ridge
                    if (y > 0.28 && y < 0.62) {
                        const brow = Math.exp(-Math.pow(y - 0.40, 2) / 0.018) * Math.exp(-Math.pow(x, 2) / 0.38);
                        z += brow * 0.17;
                    }

                    // Eye sockets: Anatomical orbital recesses (bilateral)
                    for (let side of [-0.31, 0.31]) {
                        const dEye = Math.hypot(x - side, y - 0.24);
                        if (dEye < 0.23) {
                            const indent = Math.cos((dEye / 0.23) * (Math.PI / 2));
                            z -= indent * 0.23;
                            // Eyeball bulge within orbital margin
                            if (dEye < 0.12) {
                                const bulge = Math.cos((dEye / 0.12) * (Math.PI / 2));
                                z += bulge * 0.13;
                            }
                        }
                    }

                    // Nose structure: Dorsal bridge, pronasale tip, and alar wings
                    if (y > -0.18 && y < 0.34 && Math.abs(x) < 0.25) {
                        const bridgeWidth = 0.08 + (0.34 - y) * 0.25;
                        if (Math.abs(x) < bridgeWidth) {
                            const hFactor = 1.0 - Math.abs(x) / bridgeWidth;
                            // Nose tip apex at y ~ -0.06
                            const tipMult = 1.0 + 0.95 * Math.exp(-Math.pow(y - (-0.06), 2) / 0.012);
                            z += hFactor * 0.34 * tipMult;
                        }
                        // Nostril flares
                        for (let nSide of [-0.14, 0.14]) {
                            const dNostril = Math.hypot(x - nSide, y - (-0.10));
                            if (dNostril < 0.10) {
                                z += Math.cos((dNostril / 0.10) * (Math.PI / 2)) * 0.12;
                            }
                        }
                    }

                    // Cheeks / Zygomatic arch
                    for (let cSide of [-0.46, 0.46]) {
                        const dCheek = Math.hypot(x - cSide, y - 0.02);
                        if (dCheek < 0.28) {
                            z += Math.cos((dCheek / 0.28) * (Math.PI / 2)) * 0.16;
                        }
                    }

                    // Lips & Mouth: Philtrum, Cupid's Bow, Upper and Lower Lips
                    if (y > -0.46 && y < -0.18 && Math.abs(x) < 0.28) {
                        const lipW = 0.26;
                        if (Math.abs(x) < lipW) {
                            const lipEnv = (1.0 - Math.pow(Math.abs(x) / lipW, 2));
                            // Upper lip with Cupid's bow dip
                            if (y > -0.30) {
                                const cupid = 1.0 - 0.35 * Math.exp(-Math.pow(x, 2) / 0.0035);
                                const uProf = Math.sin(Math.max(0.0, (y - (-0.30)) / 0.10) * Math.PI);
                                z += lipEnv * uProf * 0.17 * cupid;
                            } else {
                                // Lower lip fullness
                                const lProf = Math.sin(Math.max(0.0, (y - (-0.45)) / 0.15) * Math.PI);
                                z += lipEnv * lProf * 0.20;
                            }
                        }
                    }

                    // Chin: Mental protuberance
                    if (y > -0.74 && y < -0.44 && Math.abs(x) < 0.26) {
                        const chinF = (1.0 - Math.abs(x) / 0.26) * Math.sin(((y - (-0.74)) / 0.30) * Math.PI);
                        z += chinF * 0.23;
                    }
                }

                // Mandibular angle & jawline tapering towards chin
                if (y < -0.15 && y > -0.76) {
                    const t = (y - (-0.15)) / (-0.61);
                    x *= (1.0 - t * 0.36);
                    if (z > 0) z *= (1.0 - t * 0.14);
                }

                // --- 3. Anatomical Ear Bilateral Protrusions ---
                if (y > -0.16 && y < 0.34 && Math.abs(x) > 0.60) {
                    const earY = (y - 0.09) / 0.25;
                    const earShape = Math.max(0, 1 - Math.pow(earY, 2));
                    const earSide = Math.sign(x);
                    if (z > -0.35 && z < 0.10) {
                        x += earSide * earShape * 0.18;
                        z += earShape * 0.08;
                    }
                }

                // --- 4. Descending Cervical Neck Column ---
                if (y <= -0.70) {
                    const neckT = Math.min(1.0, (y - (-0.70)) / (-0.65));
                    const neckRad = 0.44 + neckT * 0.24; // Flaring into circular base
                    const radXZ = Math.hypot(x, z);
                    if (radXZ > 0.001) {
                        x = (x / radXZ) * neckRad;
                        z = (z / radXZ) * neckRad * 0.94;
                        z -= neckT * 0.12; // Anatomical cervical column backward incline
                    }
                }

                pos.setXYZ(i, x, y, z);
            }

            geometry.computeVertexNormals();

            // 1. Primary Holographic Cyan Wireframe Material
            this.meshMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                wireframe: true,
                transparent: true,
                opacity: 0.42,
                blending: THREE.AdditiveBlending
            });

            this.faceMesh = new THREE.Mesh(geometry, this.meshMaterial);
            this.faceGroup.add(this.faceMesh);

            // 2. Volumetric Luminescent Inner Core (Gives true holographic body)
            const coreMaterial = new THREE.MeshBasicMaterial({
                color: 0x0284c7,
                transparent: true,
                opacity: 0.09,
                blending: THREE.AdditiveBlending,
                side: THREE.DoubleSide
            });
            const coreMesh = new THREE.Mesh(geometry, coreMaterial);
            coreMesh.scale.set(0.97, 0.97, 0.97);
            this.faceGroup.add(coreMesh);

            // 3. Glowing Point Grid Matrix (Digital shimmer at intersections)
            const matrixPointsMaterial = new THREE.PointsMaterial({
                color: 0x38bdf8,
                size: 0.022,
                transparent: true,
                opacity: 0.55,
                blending: THREE.AdditiveBlending
            });
            const matrixPoints = new THREE.Points(geometry, matrixPointsMaterial);
            this.faceGroup.add(matrixPoints);
        }

        /**
         * Dedicated High-Fidelity Eye Contours & Ear Auricle Details
         */
        buildEyeAndEarDetails() {
            // Detailed Orbital & Ocular Eyelid Rings for Left & Right Eyes
            const eyeCenters = [
                { x: -0.31, y: 0.24, z: 0.70 },
                { x: 0.31, y: 0.24, z: 0.70 }
            ];

            const eyeLineMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.85,
                blending: THREE.AdditiveBlending
            });

            eyeCenters.forEach(eye => {
                // Eyelid Ring
                const ringPoints = [];
                const segments = 24;
                for (let i = 0; i <= segments; i++) {
                    const theta = (i / segments) * Math.PI * 2;
                    const rx = Math.cos(theta) * 0.11;
                    const ry = Math.sin(theta) * 0.055;
                    ringPoints.push(new THREE.Vector3(eye.x + rx, eye.y + ry, eye.z));
                }
                const ringGeo = new THREE.BufferGeometry().setFromPoints(ringPoints);
                const eyeLine = new THREE.Line(ringGeo, eyeLineMat);
                this.faceGroup.add(eyeLine);

                // Pupil / Iris Focal Point
                const irisGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(eye.x, eye.y, eye.z + 0.015)
                ]);
                const irisMat = new THREE.PointsMaterial({
                    color: 0x38bdf8,
                    size: 0.065,
                    transparent: true,
                    opacity: 0.95,
                    blending: THREE.AdditiveBlending
                });
                const irisPoint = new THREE.Points(irisGeo, irisMat);
                this.faceGroup.add(irisPoint);
            });

            // Ear Auricle Cartilage Outlines
            const earLineMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.6,
                blending: THREE.AdditiveBlending
            });

            [-1, 1].forEach(side => {
                const earPoints = [];
                const earSegs = 16;
                for (let i = 0; i <= earSegs; i++) {
                    const t = (i / earSegs) * Math.PI;
                    const ex = side * (0.76 + Math.sin(t) * 0.10);
                    const ey = 0.09 + Math.cos(t) * 0.18;
                    const ez = -0.05 + Math.sin(t) * 0.08;
                    earPoints.push(new THREE.Vector3(ex, ey, ez));
                }
                const earGeo = new THREE.BufferGeometry().setFromPoints(earPoints);
                const earLine = new THREE.Line(earGeo, earLineMat);
                this.faceGroup.add(earLine);
            });
        }

        /**
         * 68 Biometric Facial Landmark Points Mapped to Anatomical Proportions
         */
        buildLandmarkPoints() {
            const landmarkPositions = [
                // Jawline & Mandible Contour (0-16)
                [-0.72, 0.28, -0.05], [-0.68, 0.12, 0.10], [-0.64, -0.05, 0.22], [-0.58, -0.22, 0.36],
                [-0.50, -0.38, 0.48], [-0.38, -0.52, 0.60], [-0.24, -0.62, 0.68], [-0.12, -0.68, 0.72],
                [0.0, -0.70, 0.74],
                [0.12, -0.68, 0.72], [0.24, -0.62, 0.68], [0.38, -0.52, 0.60], [0.50, -0.38, 0.48],
                [0.58, -0.22, 0.36], [0.64, -0.05, 0.22], [0.68, 0.12, 0.10], [0.72, 0.28, -0.05],

                // Left Eyebrow (17-21)
                [-0.52, 0.38, 0.60], [-0.42, 0.44, 0.68], [-0.30, 0.45, 0.72], [-0.18, 0.42, 0.74], [-0.08, 0.38, 0.72],

                // Right Eyebrow (22-26)
                [0.08, 0.38, 0.72], [0.18, 0.42, 0.74], [0.30, 0.45, 0.72], [0.42, 0.44, 0.68], [0.52, 0.38, 0.60],

                // Nose Bridge & Tip (27-35)
                [0.0, 0.30, 0.75], [0.0, 0.18, 0.82], [0.0, 0.06, 0.89], [0.0, -0.06, 0.98],
                [-0.14, -0.12, 0.88], [-0.07, -0.13, 0.95], [0.0, -0.14, 0.96], [0.07, -0.13, 0.95], [0.14, -0.12, 0.88],

                // Left Eye Perimeter (36-41)
                [-0.42, 0.24, 0.65], [-0.34, 0.28, 0.70], [-0.24, 0.28, 0.70], [-0.16, 0.24, 0.68],
                [-0.24, 0.20, 0.68], [-0.34, 0.20, 0.68],

                // Right Eye Perimeter (42-47)
                [0.16, 0.24, 0.68], [0.24, 0.28, 0.70], [0.34, 0.28, 0.70], [0.42, 0.24, 0.65],
                [0.34, 0.20, 0.68], [0.24, 0.20, 0.68],

                // Outer & Inner Lips (48-67)
                [-0.24, -0.29, 0.78], [-0.15, -0.24, 0.86], [-0.07, -0.22, 0.90], [0.0, -0.23, 0.91],
                [0.07, -0.22, 0.90], [0.15, -0.24, 0.86], [0.24, -0.29, 0.78], [0.15, -0.36, 0.86],
                [0.07, -0.38, 0.89], [0.0, -0.39, 0.90], [-0.07, -0.38, 0.89], [-0.15, -0.36, 0.86],

                [-0.18, -0.29, 0.80], [-0.07, -0.26, 0.86], [0.0, -0.26, 0.87], [0.07, -0.26, 0.86],
                [0.18, -0.29, 0.80], [0.07, -0.33, 0.86], [0.0, -0.34, 0.87], [-0.07, -0.33, 0.86]
            ];

            const pointCount = landmarkPositions.length;
            const pointGeo = new THREE.BufferGeometry();
            const positions = new Float32Array(pointCount * 3);

            for (let i = 0; i < pointCount; i++) {
                positions[i * 3] = landmarkPositions[i][0];
                positions[i * 3 + 1] = landmarkPositions[i][1];
                positions[i * 3 + 2] = landmarkPositions[i][2];
            }

            pointGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

            this.landmarkMaterial = new THREE.PointsMaterial({
                color: 0x00f0ff,
                size: 0.055,
                transparent: true,
                opacity: 0.95,
                blending: THREE.AdditiveBlending
            });

            this.landmarks = new THREE.Points(pointGeo, this.landmarkMaterial);
            this.faceGroup.add(this.landmarks);
        }

        /**
         * Moving Horizontal Laser Scanning Plane & Cyan Light
         */
        buildLaserPlane() {
            const laserGeo = new THREE.PlaneGeometry(2.4, 0.03);
            this.laserMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.95,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending
            });

            this.laserMesh = new THREE.Mesh(laserGeo, this.laserMaterial);
            this.laserMesh.rotation.x = Math.PI / 2;
            this.laserMesh.position.set(0, 0, 0);

            // Planar Laser Halo
            const haloGeo = new THREE.PlaneGeometry(2.6, 0.28);
            this.haloMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.28,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending
            });
            this.laserHalo = new THREE.Mesh(haloGeo, this.haloMaterial);
            this.laserHalo.rotation.x = Math.PI / 2;
            this.laserMesh.add(this.laserHalo);

            this.faceGroup.add(this.laserMesh);
        }

        /**
         * Circular Holographic Base Platform with Concentric Neon Rings
         */
        buildHolographicPlatform() {
            const ringColors = [0x00f0ff, 0x3b82f6, 0xa855f7];
            const radii = [1.2, 1.45, 1.7];

            radii.forEach((r, idx) => {
                const ringGeo = new THREE.RingGeometry(r - 0.02, r, 64);
                const ringMat = new THREE.MeshBasicMaterial({
                    color: ringColors[idx],
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.5 - idx * 0.1,
                    blending: THREE.AdditiveBlending
                });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.rotation.x = Math.PI / 2;
                ring.position.y = -1.35;
                this.platformGroup.add(ring);
            });

            // Glowing ground emission disk directly under neck pedestal
            const groundDiskGeo = new THREE.CircleGeometry(0.75, 48);
            const groundDiskMat = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.15,
                blending: THREE.AdditiveBlending
            });
            const groundDisk = new THREE.Mesh(groundDiskGeo, groundDiskMat);
            groundDisk.rotation.x = Math.PI / 2;
            groundDisk.position.y = -1.35;
            this.platformGroup.add(groundDisk);

            // Radial tick marks
            const tickCount = 28;
            const tickGeo = new THREE.BufferGeometry();
            const tickPos = [];
            for (let i = 0; i < tickCount; i++) {
                const angle = (i / tickCount) * Math.PI * 2;
                const x1 = Math.cos(angle) * 1.45;
                const z1 = Math.sin(angle) * 1.45;
                const x2 = Math.cos(angle) * 1.62;
                const z2 = Math.sin(angle) * 1.62;
                tickPos.push(x1, -1.35, z1, x2, -1.35, z2);
            }
            tickGeo.setAttribute("position", new THREE.Float32BufferAttribute(tickPos, 3));
            const tickMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.5 });
            this.platformTicks = new THREE.LineSegments(tickGeo, tickMat);
            this.platformGroup.add(this.platformTicks);

            this.scene.add(this.platformGroup);
        }

        /**
         * Floating Ambient Cyber Dust Particles
         */
        buildParticleAura() {
            const particleCount = 240;
            const geo = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            const velocities = [];

            for (let i = 0; i < particleCount; i++) {
                positions[i * 3] = (Math.random() - 0.5) * 4.5;
                positions[i * 3 + 1] = (Math.random() - 0.5) * 4.0;
                positions[i * 3 + 2] = (Math.random() - 0.5) * 3.5;

                velocities.push({
                    y: 0.003 + Math.random() * 0.006,
                    sway: Math.random() * Math.PI * 2
                });
            }

            geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
            this.particleVelocities = velocities;

            const mat = new THREE.PointsMaterial({
                color: 0x00f0ff,
                size: 0.035,
                transparent: true,
                opacity: 0.65,
                blending: THREE.AdditiveBlending
            });

            this.particles = new THREE.Points(geo, mat);
            this.scene.add(this.particles);
        }

        /**
         * Mouse Tracking & Interactive Drag Orbiting
         */
        bindEvents() {
            const el = this.container;

            el.addEventListener("mousemove", (e) => {
                const rect = el.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
                const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);

                this.mouse.targetX = x * 0.45;
                this.mouse.targetY = y * 0.35;

                if (this.isDragging) {
                    const deltaX = e.clientX - this.previousMousePosition.x;
                    const deltaY = e.clientY - this.previousMousePosition.y;

                    this.faceGroup.rotation.y += deltaX * 0.01;
                    this.faceGroup.rotation.x += deltaY * 0.01;

                    this.previousMousePosition = { x: e.clientX, y: e.clientY };
                }
            });

            el.addEventListener("mousedown", (e) => {
                this.isDragging = true;
                this.previousMousePosition = { x: e.clientX, y: e.clientY };
            });

            window.addEventListener("mouseup", () => {
                this.isDragging = false;
            });

            // Touch events for mobile
            el.addEventListener("touchstart", (e) => {
                if (e.touches.length === 1) {
                    this.isDragging = true;
                    this.previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
                }
            }, { passive: true });

            el.addEventListener("touchmove", (e) => {
                if (this.isDragging && e.touches.length === 1) {
                    const deltaX = e.touches[0].clientX - this.previousMousePosition.x;
                    const deltaY = e.touches[0].clientY - this.previousMousePosition.y;

                    this.faceGroup.rotation.y += deltaX * 0.01;
                    this.faceGroup.rotation.x += deltaY * 0.01;

                    this.previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
                }
            }, { passive: true });

            window.addEventListener("touchend", () => {
                this.isDragging = false;
            });

            // Reset View Button
            const resetBtn = document.getElementById("resetScannerBtn");
            if (resetBtn) {
                resetBtn.addEventListener("click", () => {
                    this.resetView();
                });
            }

            // Window Resize
            window.addEventListener("resize", () => {
                if (!this.container || !this.renderer || !this.camera) return;
                const w = this.container.clientWidth;
                const h = this.container.clientHeight;
                this.camera.aspect = w / h;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(w, h);
            });
        }

        resetView() {
            if (window.gsap) {
                gsap.to(this.faceGroup.rotation, { x: 0, y: 0, z: 0, duration: 0.8, ease: "power2.out" });
                gsap.to(this.faceGroup.position, { x: 0, y: 0, z: 0, duration: 0.8, ease: "power2.out" });
            } else {
                this.faceGroup.rotation.set(0, 0, 0);
                this.faceGroup.position.set(0, 0, 0);
            }
            this.mouse.targetX = 0;
            this.mouse.targetY = 0;
        }

        /**
         * Triggered when an image starts analysis
         */
        startScan() {
            this.isScanning = true;
            this.scanState = "scanning";
            this.laserSpeed = 2.8;

            this.laserMaterial.color.setHex(0x00f0ff);
            this.laserHalo.material.color.setHex(0x00f0ff);
            this.meshMaterial.opacity = 0.72;
            this.landmarkMaterial.size = 0.085;

            if (window.gsap) {
                gsap.to(this.meshMaterial, { opacity: 0.85, duration: 0.35, yoyo: true, repeat: -1 });
            }
        }

        /**
         * Triggered when detection finishes with real verdict
         */
        setResult(isReal, confidence) {
            this.isScanning = false;
            this.laserSpeed = 1.0;

            if (isReal) {
                this.scanState = "real";
                // Verified Authentic: Vibrant Neon Emerald
                this.meshMaterial.color.setHex(0x10b981);
                this.laserMaterial.color.setHex(0x10b981);
                this.landmarkMaterial.color.setHex(0x10b981);
            } else {
                this.scanState = "fake";
                // Flagged Deepfake: Alarm Neon Rose / Magenta
                this.meshMaterial.color.setHex(0xf43f5e);
                this.laserMaterial.color.setHex(0xf43f5e);
                this.landmarkMaterial.color.setHex(0xf43f5e);
            }

            if (window.gsap) {
                gsap.killTweensOf(this.meshMaterial);
                gsap.fromTo(this.faceGroup.scale, { x: 1.08, y: 1.08, z: 1.08 }, { x: 1, y: 1, z: 1, duration: 0.6, ease: "elastic.out(1, 0.4)" });
            }
        }

        /**
         * Reset to idle cyber cyan
         */
        reset() {
            this.isScanning = false;
            this.scanState = "idle";
            this.laserSpeed = 1.2;
            this.meshMaterial.color.setHex(0x00f0ff);
            this.meshMaterial.opacity = 0.42;
            this.laserMaterial.color.setHex(0x00f0ff);
            this.landmarkMaterial.color.setHex(0x00f0ff);
            this.landmarkMaterial.size = 0.055;
            if (window.gsap) gsap.killTweensOf(this.meshMaterial);
        }

        /**
         * Main Render & Animation Loop
         */
        animate() {
            requestAnimationFrame(this.animate);
            const delta = this.clock.getDelta();
            const elapsed = this.clock.getElapsedTime();

            // 1. Subtle idle breathing & mouse interpolation
            if (!this.isDragging) {
                this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
                this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

                const breathing = Math.sin(elapsed * 1.5) * 0.035;
                this.faceGroup.rotation.y = this.mouse.x + Math.sin(elapsed * 0.7) * 0.10;
                this.faceGroup.rotation.x = -this.mouse.y + breathing;
            }

            // 2. Moving Laser Sweep
            this.laserY += this.laserDirection * this.laserSpeed * delta;
            if (this.laserY > 1.15) {
                this.laserY = 1.15;
                this.laserDirection = -1;
            } else if (this.laserY < -1.15) {
                this.laserY = -1.15;
                this.laserDirection = 1;
            }
            this.laserMesh.position.y = this.laserY;

            // 3. Rotate Holographic Base Platform
            this.platformGroup.rotation.y -= 0.006;
            if (this.platformTicks) this.platformTicks.rotation.y += 0.003;

            // 4. Update Ambient Particles
            if (this.particles) {
                const pos = this.particles.geometry.attributes.position.array;
                for (let i = 0; i < this.particleVelocities.length; i++) {
                    pos[i * 3 + 1] += this.particleVelocities[i].y;
                    pos[i * 3] += Math.sin(elapsed + this.particleVelocities[i].sway) * 0.001;

                    if (pos[i * 3 + 1] > 2.2) {
                        pos[i * 3 + 1] = -1.8;
                    }
                }
                this.particles.geometry.attributes.position.needsUpdate = true;
            }

            // 5. Update Telemetry HUD
            this.frameCount++;
            if (elapsed - this.lastFpsUpdate > 0.5) {
                if (this.fpsEl) this.fpsEl.textContent = (this.frameCount / (elapsed - this.lastFpsUpdate)).toFixed(1);
                this.frameCount = 0;
                this.lastFpsUpdate = elapsed;
            }
            if (this.rotEl) {
                const deg = THREE.MathUtils.radToDeg(this.faceGroup.rotation.y);
                this.rotEl.textContent = deg.toFixed(1);
            }

            this.renderer.render(this.scene, this.camera);
        }
    }

    // Initialize globally when DOM is ready
    window.addEventListener("DOMContentLoaded", function () {
        if (typeof THREE !== "undefined" && document.getElementById("faceScanner3DContainer")) {
            window.FaceScanner3D = new HolographicFaceScanner("faceScanner3DContainer");
        }
    });

})();
