/**
 * FACEGUARD AI - Advanced 3D Holographic Face Scanner
 * Module: static/js/face_scanner_3d.js
 * Powered by Three.js (r128)
 * 
 * Phase 3 Upgrade:
 * - Fine triangular biometric landmark contour networks (Jawline, Brows, Nose, Eyes, Lips)
 * - 3D Holographic Cyber Targeting Framing Brackets & Crosshair Notches matching Image 2
 * - Upward Holographic Projection Emitter Light Cone with Additive Volumetric Luminescence
 * - Pulsating landmark nodes, glowing connection lines, and animated wireframe illumination
 * - Multi-ring rotating scanning pedestal with ground emission flares
 * - Preserves interactive mouse/touch controls, FPS/ROT telemetry, and Flask detection hooks
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
            this.hudGroup = new THREE.Group();
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

            // Dynamic materials for pulsation
            this.contourMaterials = [];

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

            // 1. Scene with deep cyber fog
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(0x040711, 0.15);

            // 2. Camera
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            this.camera.position.set(0, 0, 4.3);

            // 3. High-Performance WebGL Renderer
            this.renderer = new THREE.WebGLRenderer({
                antialias: true,
                alpha: true,
                powerPreference: "high-performance"
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.25;
            this.container.appendChild(this.renderer.domElement);

            // 4. Cyber Illumination Lights
            const ambientLight = new THREE.AmbientLight(0x00f0ff, 0.95);
            this.scene.add(ambientLight);

            const frontalPointLight = new THREE.PointLight(0x00f0ff, 3.2, 12);
            frontalPointLight.position.set(0, 1.8, 3.5);
            this.scene.add(frontalPointLight);

            const rightRimLight = new THREE.PointLight(0x06b6d4, 2.4, 8);
            rightRimLight.position.set(2.8, 0.5, 1.8);
            this.scene.add(rightRimLight);

            const leftRimLight = new THREE.PointLight(0xa855f7, 2.5, 8);
            leftRimLight.position.set(-2.8, -0.5, 1.8);
            this.scene.add(leftRimLight);

            // 5. Build 3D Entities
            this.buildFacialMesh();
            this.buildEyeAndEarDetails();
            this.buildLandmarkPoints();
            this.buildLandmarkContours();
            this.buildHolographicHUDFrame();
            this.buildLaserPlane();
            this.buildHolographicPlatform();
            this.buildProjectionEmitterCone();
            this.buildParticleAura();

            this.scene.add(this.faceGroup);
            this.scene.add(this.hudGroup);

            // 6. Bind User Interaction Events
            this.bindEvents();

            // 7. Start Main Render & Animation Loop
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

                // --- Vertical Proportions: Head + Neck ---
                if (y > -0.2) {
                    y = 0.2 + (y - (-0.2)) * 0.95;
                } else {
                    y = 0.2 + (y - (-0.2)) * 1.45;
                }

                x *= 0.88;
                z *= 1.05;

                // --- Frontal Facial Features Sculpting (z > -0.2) ---
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
                            const tipMult = 1.0 + 0.95 * Math.exp(-Math.pow(y - (-0.06), 2) / 0.012);
                            z += hFactor * 0.34 * tipMult;
                        }
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
                            if (y > -0.30) {
                                const cupid = 1.0 - 0.35 * Math.exp(-Math.pow(x, 2) / 0.0035);
                                const uProf = Math.sin(Math.max(0.0, (y - (-0.30)) / 0.10) * Math.PI);
                                z += lipEnv * uProf * 0.17 * cupid;
                            } else {
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

                // Mandibular angle & jawline tapering
                if (y < -0.15 && y > -0.76) {
                    const t = (y - (-0.15)) / (-0.61);
                    x *= (1.0 - t * 0.36);
                    if (z > 0) z *= (1.0 - t * 0.14);
                }

                // Anatomical Ear Bilateral Protrusions
                if (y > -0.16 && y < 0.34 && Math.abs(x) > 0.60) {
                    const earY = (y - 0.09) / 0.25;
                    const earShape = Math.max(0, 1 - Math.pow(earY, 2));
                    const earSide = Math.sign(x);
                    if (z > -0.35 && z < 0.10) {
                        x += earSide * earShape * 0.18;
                        z += earShape * 0.08;
                    }
                }

                // Descending Cervical Neck Column
                if (y <= -0.70) {
                    const neckT = Math.min(1.0, (y - (-0.70)) / (-0.65));
                    const neckRad = 0.44 + neckT * 0.24;
                    const radXZ = Math.hypot(x, z);
                    if (radXZ > 0.001) {
                        x = (x / radXZ) * neckRad;
                        z = (z / radXZ) * neckRad * 0.94;
                        z -= neckT * 0.12;
                    }
                }

                pos.setXYZ(i, x, y, z);
            }

            geometry.computeVertexNormals();

            // 1. Primary Holographic Cyan Wireframe
            this.meshMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                wireframe: true,
                transparent: true,
                opacity: 0.45,
                blending: THREE.AdditiveBlending
            });

            this.faceMesh = new THREE.Mesh(geometry, this.meshMaterial);
            this.faceGroup.add(this.faceMesh);

            // 2. Volumetric Luminescent Inner Core (Gives true holographic substance)
            const coreMaterial = new THREE.MeshBasicMaterial({
                color: 0x0284c7,
                transparent: true,
                opacity: 0.10,
                blending: THREE.AdditiveBlending,
                side: THREE.DoubleSide
            });
            const coreMesh = new THREE.Mesh(geometry, coreMaterial);
            coreMesh.scale.set(0.97, 0.97, 0.97);
            this.faceGroup.add(coreMesh);

            // 3. Glowing Matrix Point Grid
            const matrixPointsMaterial = new THREE.PointsMaterial({
                color: 0x38bdf8,
                size: 0.024,
                transparent: true,
                opacity: 0.60,
                blending: THREE.AdditiveBlending
            });
            const matrixPoints = new THREE.Points(geometry, matrixPointsMaterial);
            this.faceGroup.add(matrixPoints);
        }

        /**
         * Dedicated High-Fidelity Eye Contours & Ear Auricle Details
         */
        buildEyeAndEarDetails() {
            const eyeCenters = [
                { x: -0.31, y: 0.24, z: 0.70 },
                { x: 0.31, y: 0.24, z: 0.70 }
            ];

            const eyeLineMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.9,
                blending: THREE.AdditiveBlending
            });
            this.contourMaterials.push(eyeLineMat);

            eyeCenters.forEach(eye => {
                const ringPoints = [];
                const segments = 28;
                for (let i = 0; i <= segments; i++) {
                    const theta = (i / segments) * Math.PI * 2;
                    const rx = Math.cos(theta) * 0.115;
                    const ry = Math.sin(theta) * 0.058;
                    ringPoints.push(new THREE.Vector3(eye.x + rx, eye.y + ry, eye.z));
                }
                const ringGeo = new THREE.BufferGeometry().setFromPoints(ringPoints);
                const eyeLine = new THREE.Line(ringGeo, eyeLineMat);
                this.faceGroup.add(eyeLine);

                // Pupil / Iris Focal Point
                const irisGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(eye.x, eye.y, eye.z + 0.018)
                ]);
                const irisMat = new THREE.PointsMaterial({
                    color: 0x38bdf8,
                    size: 0.07,
                    transparent: true,
                    opacity: 0.98,
                    blending: THREE.AdditiveBlending
                });
                const irisPoint = new THREE.Points(irisGeo, irisMat);
                this.faceGroup.add(irisPoint);
            });

            // Ear Auricle Cartilage Outlines
            const earLineMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.65,
                blending: THREE.AdditiveBlending
            });
            this.contourMaterials.push(earLineMat);

            [-1, 1].forEach(side => {
                const earPoints = [];
                const earSegs = 20;
                for (let i = 0; i <= earSegs; i++) {
                    const t = (i / earSegs) * Math.PI;
                    const ex = side * (0.76 + Math.sin(t) * 0.11);
                    const ey = 0.09 + Math.cos(t) * 0.19;
                    const ez = -0.05 + Math.sin(t) * 0.09;
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
            this.landmarkCoords = [
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

            const pointCount = this.landmarkCoords.length;
            const pointGeo = new THREE.BufferGeometry();
            const positions = new Float32Array(pointCount * 3);

            for (let i = 0; i < pointCount; i++) {
                positions[i * 3] = this.landmarkCoords[i][0];
                positions[i * 3 + 1] = this.landmarkCoords[i][1];
                positions[i * 3 + 2] = this.landmarkCoords[i][2];
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
         * Fine Triangular Biometric Landmark Contour Networks
         */
        buildLandmarkContours() {
            const coords = this.landmarkCoords;
            const contourMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.70,
                blending: THREE.AdditiveBlending
            });
            this.contourMaterials.push(contourMat);

            const addLineLoop = (indices, closed = false) => {
                const points = indices.map(idx => new THREE.Vector3(...coords[idx]));
                if (closed && points.length > 0) points.push(points[0].clone());
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geo, contourMat);
                this.faceGroup.add(line);
            };

            // 1. Jawline Contour (0-16)
            addLineLoop([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]);

            // 2. Eyebrow Arcs (17-21, 22-26)
            addLineLoop([17, 18, 19, 20, 21]);
            addLineLoop([22, 23, 24, 25, 26]);

            // 3. Nose Bridge & Nostril Base (27-30, 31-35)
            addLineLoop([27, 28, 29, 30]);
            addLineLoop([31, 32, 33, 34, 35, 30]);

            // 4. Closed Eye Loops (36-41, 42-47)
            addLineLoop([36, 37, 38, 39, 40, 41], true);
            addLineLoop([42, 43, 44, 45, 46, 47], true);

            // 5. Outer & Inner Lip Loops (48-59, 60-67)
            addLineLoop([48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59], true);
            addLineLoop([60, 61, 62, 63, 64, 65, 66, 67], true);

            // 6. Forensic Triangulation Connections (Nose to Eyes, Brows to Forehead)
            const fineMat = new THREE.LineBasicMaterial({
                color: 0x06b6d4,
                transparent: true,
                opacity: 0.35,
                blending: THREE.AdditiveBlending
            });
            this.contourMaterials.push(fineMat);

            const triPairs = [
                [27, 39], [27, 42], [28, 39], [28, 42],
                [30, 48], [30, 54], [33, 51],
                [36, 0], [45, 16], [48, 4], [54, 12],
                [19, 27], [24, 27]
            ];
            const triPoints = [];
            triPairs.forEach(([a, b]) => {
                triPoints.push(new THREE.Vector3(...coords[a]), new THREE.Vector3(...coords[b]));
            });
            const triGeo = new THREE.BufferGeometry().setFromPoints(triPoints);
            const triLines = new THREE.LineSegments(triGeo, fineMat);
            this.faceGroup.add(triLines);
        }

        /**
         * 3D Holographic Cyber Targeting Framing Brackets & Crosshair Notches
         * (Matches the cyan HUD reticle frame surrounding the head in Image 2)
         */
        buildHolographicHUDFrame() {
            const frameMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.85,
                blending: THREE.AdditiveBlending
            });
            this.contourMaterials.push(frameMat);

            // Outer Reticle Dimensions surrounding the head
            const minX = -1.35, maxX = 1.35;
            const minY = -1.25, maxY = 1.35;
            const z = 0.1;
            const bracketLen = 0.35;

            const bracketPoints = [];

            // Top-Left Corner Bracket
            bracketPoints.push(new THREE.Vector3(minX, maxY - bracketLen, z), new THREE.Vector3(minX, maxY, z));
            bracketPoints.push(new THREE.Vector3(minX, maxY, z), new THREE.Vector3(minX + bracketLen, maxY, z));

            // Top-Right Corner Bracket
            bracketPoints.push(new THREE.Vector3(maxX - bracketLen, maxY, z), new THREE.Vector3(maxX, maxY, z));
            bracketPoints.push(new THREE.Vector3(maxX, maxY, z), new THREE.Vector3(maxX, maxY - bracketLen, z));

            // Bottom-Left Corner Bracket
            bracketPoints.push(new THREE.Vector3(minX, minY + bracketLen, z), new THREE.Vector3(minX, minY, z));
            bracketPoints.push(new THREE.Vector3(minX, minY, z), new THREE.Vector3(minX + bracketLen, minY, z));

            // Bottom-Right Corner Bracket
            bracketPoints.push(new THREE.Vector3(maxX - bracketLen, minY, z), new THREE.Vector3(maxX, minY, z));
            bracketPoints.push(new THREE.Vector3(maxX, minY, z), new THREE.Vector3(maxX, minY + bracketLen, z));

            // Lateral Tick Notches (Left & Right)
            bracketPoints.push(new THREE.Vector3(minX - 0.08, 0.05, z), new THREE.Vector3(minX + 0.08, 0.05, z));
            bracketPoints.push(new THREE.Vector3(maxX - 0.08, 0.05, z), new THREE.Vector3(maxX + 0.08, 0.05, z));

            // Top & Bottom Crosshair Ticks
            bracketPoints.push(new THREE.Vector3(0, maxY - 0.08, z), new THREE.Vector3(0, maxY + 0.08, z));
            bracketPoints.push(new THREE.Vector3(0, minY - 0.08, z), new THREE.Vector3(0, minY + 0.08, z));

            const bracketGeo = new THREE.BufferGeometry().setFromPoints(bracketPoints);
            const brackets = new THREE.LineSegments(bracketGeo, frameMat);
            this.hudGroup.add(brackets);

            // Subtle Outer Framing Border
            const borderMat = new THREE.LineBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.20,
                blending: THREE.AdditiveBlending
            });
            const borderPoints = [
                new THREE.Vector3(minX, maxY, z), new THREE.Vector3(maxX, maxY, z),
                new THREE.Vector3(maxX, maxY, z), new THREE.Vector3(maxX, minY, z),
                new THREE.Vector3(maxX, minY, z), new THREE.Vector3(minX, minY, z),
                new THREE.Vector3(minX, minY, z), new THREE.Vector3(minX, maxY, z)
            ];
            const borderGeo = new THREE.BufferGeometry().setFromPoints(borderPoints);
            const borderLines = new THREE.LineSegments(borderGeo, borderMat);
            this.hudGroup.add(borderLines);
        }

        /**
         * Upward Holographic Projection Emitter Light Cone
         */
        buildProjectionEmitterCone() {
            // Inverted cone radiating upward from circular platform to chin
            const coneGeo = new THREE.CylinderGeometry(0.85, 0.65, 0.70, 36, 1, true);
            this.emitterConeMat = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.12,
                blending: THREE.AdditiveBlending,
                depthWrite: false
            });
            const emitterCone = new THREE.Mesh(coneGeo, this.emitterConeMat);
            emitterCone.position.set(0, -1.0, 0);
            this.platformGroup.add(emitterCone);
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
                opacity: 0.30,
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
                    opacity: 0.55 - idx * 0.1,
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
                opacity: 0.18,
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
            const tickMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.55 });
            this.platformTicks = new THREE.LineSegments(tickGeo, tickMat);
            this.platformGroup.add(this.platformTicks);

            this.scene.add(this.platformGroup);
        }

        /**
         * Floating Ambient Cyber Dust Particles
         */
        buildParticleAura() {
            const particleCount = 250;
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
            this.meshMaterial.opacity = 0.75;
            this.landmarkMaterial.size = 0.085;

            if (window.gsap) {
                gsap.to(this.meshMaterial, { opacity: 0.88, duration: 0.35, yoyo: true, repeat: -1 });
            }
        }

        /**
         * Triggered when detection finishes with real verdict
         */
        setResult(isReal, confidence) {
            this.isScanning = false;
            this.laserSpeed = 1.0;

            const targetHex = isReal ? 0x10b981 : 0xf43f5e;
            this.scanState = isReal ? "real" : "fake";

            this.meshMaterial.color.setHex(targetHex);
            this.laserMaterial.color.setHex(targetHex);
            this.landmarkMaterial.color.setHex(targetHex);

            this.contourMaterials.forEach(mat => {
                mat.color.setHex(targetHex);
            });

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
            this.meshMaterial.opacity = 0.45;
            this.laserMaterial.color.setHex(0x00f0ff);
            this.landmarkMaterial.color.setHex(0x00f0ff);
            this.landmarkMaterial.size = 0.055;

            this.contourMaterials.forEach(mat => {
                mat.color.setHex(0x00f0ff);
            });

            if (window.gsap) gsap.killTweensOf(this.meshMaterial);
        }

        /**
         * Main Render & Animation Loop
         */
        animate() {
            requestAnimationFrame(this.animate);
            const delta = this.clock.getDelta();
            const elapsed = this.clock.getElapsedTime();

            // 1. Idle breathing & mouse interpolation
            if (!this.isDragging) {
                this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
                this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

                const breathing = Math.sin(elapsed * 1.5) * 0.035;
                this.faceGroup.rotation.y = this.mouse.x + Math.sin(elapsed * 0.7) * 0.10;
                this.faceGroup.rotation.x = -this.mouse.y + breathing;
            }

            // 2. Subtle Landmark Pulsing & Wireframe Illumination Shimmer
            if (this.landmarkMaterial) {
                const pulse = 0.055 + Math.sin(elapsed * 3.0) * 0.012;
                this.landmarkMaterial.size = pulse;
            }
            if (this.emitterConeMat) {
                this.emitterConeMat.opacity = 0.10 + Math.sin(elapsed * 2.0) * 0.04;
            }

            // 3. Moving Laser Sweep
            this.laserY += this.laserDirection * this.laserSpeed * delta;
            if (this.laserY > 1.15) {
                this.laserY = 1.15;
                this.laserDirection = -1;
            } else if (this.laserY < -1.15) {
                this.laserY = -1.15;
                this.laserDirection = 1;
            }
            this.laserMesh.position.y = this.laserY;

            // 4. Rotate Holographic Base Platform
            this.platformGroup.rotation.y -= 0.006;
            if (this.platformTicks) this.platformTicks.rotation.y += 0.003;

            // 5. Update Ambient Particles
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

            // 6. Update Telemetry HUD
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
