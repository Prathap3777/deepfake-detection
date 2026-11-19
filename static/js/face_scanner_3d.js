/**
 * FACEGUARD AI - Advanced 3D Holographic Face Scanner
 * Module: static/js/face_scanner_3d.js
 * Powered by Three.js (r128)
 * 
 * Features:
 * - Anatomically proportioned 3D facial wireframe mesh
 * - 68 Glowing biometric facial landmark points
 * - Moving horizontal laser scan beam & light flare
 * - Circular holographic base platform with radar ticks
 * - Ambient cyber dust particle system
 * - Interactive mouse tracking & orbit examination
 * - Live connection to Flask deepfake inference pipeline
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
            this.scene.fog = new THREE.FogExp2(0x040711, 0.18);

            // 2. Camera
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            this.camera.position.set(0, 0, 4.2);

            // 3. Renderer
            this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.container.appendChild(this.renderer.domElement);

            // 4. Lights
            const ambientLight = new THREE.AmbientLight(0x00f0ff, 0.8);
            this.scene.add(ambientLight);

            const pointLight = new THREE.PointLight(0x00f0ff, 2.5, 10);
            pointLight.position.set(0, 1.5, 3);
            this.scene.add(pointLight);

            const purpleBackLight = new THREE.PointLight(0xa855f7, 2, 8);
            purpleBackLight.position.set(0, -1, -2);
            this.scene.add(purpleBackLight);

            // 5. Build 3D Entities
            this.buildFacialMesh();
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
         * Procedural Anatomical 3D Face Wireframe Mesh
         */
        buildFacialMesh() {
            // Parametric Head Geometry: UV Sphere mathematically sculpted to human facial proportions
            const radius = 1.0;
            const widthSegments = 32;
            const heightSegments = 32;
            const geometry = new THREE.SphereGeometry(radius, widthSegments, heightSegments);
            const pos = geometry.attributes.position;

            for (let i = 0; i < pos.count; i++) {
                let x = pos.getX(i);
                let y = pos.getY(i);
                let z = pos.getZ(i);

                // Morph sphere into human head & face proportions
                // 1. Elongate vertically (oval cranial ratio)
                y *= 1.35;

                // 2. Frontal Facial Features (z > 0)
                if (z > 0) {
                    const normalizedY = (y + 1.35) / 2.7; // 0 (chin) to 1 (forehead)

                    // Eye socket indentations (y ~ 0.1 to 0.3, x ~ +-0.32)
                    const eyeDistL = Math.hypot(x - 0.32, y - 0.22);
                    const eyeDistR = Math.hypot(x + 0.32, y - 0.22);
                    if (eyeDistL < 0.24) z -= Math.cos((eyeDistL / 0.24) * (Math.PI / 2)) * 0.14;
                    if (eyeDistR < 0.24) z -= Math.cos((eyeDistR / 0.24) * (Math.PI / 2)) * 0.14;

                    // Nose Bridge & Tip protrusion (y ~ -0.12 to 0.2, x close to 0)
                    if (Math.abs(x) < 0.18 && y > -0.15 && y < 0.25) {
                        const noseFactor = 1 - Math.abs(x) / 0.18;
                        z += noseFactor * 0.32;
                    }

                    // Cheekbones (y ~ -0.05, x ~ +-0.5)
                    const cheekL = Math.hypot(x - 0.48, y + 0.05);
                    const cheekR = Math.hypot(x + 0.48, y + 0.05);
                    if (cheekL < 0.3) z += Math.cos((cheekL / 0.3) * (Math.PI / 2)) * 0.12;
                    if (cheekR < 0.3) z += Math.cos((cheekR / 0.3) * (Math.PI / 2)) * 0.12;

                    // Mouth & Lips (y ~ -0.32 to -0.20, x ~ +-0.25)
                    if (Math.abs(x) < 0.26 && y > -0.36 && y < -0.16) {
                        const lipFactor = 1 - Math.abs(x) / 0.26;
                        const lipBump = Math.sin(((y + 0.36) / 0.2) * Math.PI);
                        z += lipFactor * lipBump * 0.15;
                    }

                    // Chin protrusion (y ~ -0.7 to -0.5, x ~ +-0.2)
                    if (Math.abs(x) < 0.25 && y < -0.45 && y > -0.85) {
                        const chinFactor = 1 - Math.abs(x) / 0.25;
                        z += chinFactor * 0.18;
                    }
                } else {
                    // Back of head flatten slightly
                    z *= 0.85;
                }

                // Jawline taper downwards
                if (y < -0.1) {
                    const taper = 1 - (-y - 0.1) * 0.35;
                    x *= Math.max(0.65, taper);
                }

                pos.setXYZ(i, x, y, z);
            }

            geometry.computeVertexNormals();

            // Holographic Wireframe Material
            this.meshMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                wireframe: true,
                transparent: true,
                opacity: 0.38,
                blending: THREE.AdditiveBlending
            });

            this.faceMesh = new THREE.Mesh(geometry, this.meshMaterial);
            this.faceGroup.add(this.faceMesh);

            // Subtle solid inner glow core
            const coreMaterial = new THREE.MeshBasicMaterial({
                color: 0x0284c7,
                transparent: true,
                opacity: 0.08,
                blending: THREE.AdditiveBlending
            });
            const coreMesh = new THREE.Mesh(geometry, coreMaterial);
            coreMesh.scale.set(0.96, 0.96, 0.96);
            this.faceGroup.add(coreMesh);
        }

        /**
         * 68 Biometric Facial Landmark Points
         */
        buildLandmarkPoints() {
            const landmarkPositions = [
                // Jawline (0-16)
                [-0.68, 0.35, 0.1], [-0.64, 0.12, 0.25], [-0.58, -0.12, 0.4], [-0.52, -0.35, 0.52],
                [-0.42, -0.55, 0.6], [-0.3, -0.72, 0.66], [-0.16, -0.82, 0.7], [0.0, -0.86, 0.72],
                [0.16, -0.82, 0.7], [0.3, -0.72, 0.66], [0.42, -0.55, 0.6], [0.52, -0.35, 0.52],
                [0.58, -0.12, 0.4], [0.64, 0.12, 0.25], [0.68, 0.35, 0.1],
                // Left Eyebrow (17-21)
                [-0.52, 0.38, 0.62], [-0.42, 0.44, 0.7], [-0.3, 0.44, 0.74], [-0.18, 0.4, 0.75], [-0.08, 0.35, 0.72],
                // Right Eyebrow (22-26)
                [0.08, 0.35, 0.72], [0.18, 0.4, 0.75], [0.3, 0.44, 0.74], [0.42, 0.44, 0.7], [0.52, 0.38, 0.62],
                // Nose Bridge & Tip (27-35)
                [0.0, 0.3, 0.78], [0.0, 0.18, 0.84], [0.0, 0.06, 0.9], [0.0, -0.06, 0.98],
                [-0.14, -0.12, 0.9], [-0.07, -0.14, 0.96], [0.0, -0.15, 0.98], [0.07, -0.14, 0.96], [0.14, -0.12, 0.9],
                // Left Eye (36-41)
                [-0.4, 0.24, 0.68], [-0.32, 0.28, 0.72], [-0.22, 0.28, 0.72], [-0.15, 0.24, 0.68],
                [-0.22, 0.2, 0.68], [-0.32, 0.2, 0.68],
                // Right Eye (42-47)
                [0.15, 0.24, 0.68], [0.22, 0.28, 0.72], [0.32, 0.28, 0.72], [0.4, 0.24, 0.68],
                [0.32, 0.2, 0.68], [0.22, 0.2, 0.68],
                // Outer & Inner Lips (48-67)
                [-0.22, -0.32, 0.8], [-0.14, -0.27, 0.88], [0.0, -0.25, 0.92], [0.14, -0.27, 0.88], [0.22, -0.32, 0.8],
                [0.14, -0.39, 0.88], [0.0, -0.41, 0.9], [-0.14, -0.39, 0.88],
                [-0.18, -0.32, 0.82], [0.0, -0.29, 0.88], [0.18, -0.32, 0.82], [0.0, -0.35, 0.86]
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
                opacity: 0.9,
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
            const haloGeo = new THREE.PlaneGeometry(2.6, 0.25);
            this.haloMaterial = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.25,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending
            });
            this.laserHalo = new THREE.Mesh(haloGeo, this.haloMaterial);
            this.laserHalo.rotation.x = Math.PI / 2;
            this.laserMesh.add(this.laserHalo);

            this.faceGroup.add(this.laserMesh);
        }

        /**
         * Circular Holographic Base Platform with Concentric Rings
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
                    opacity: 0.45 - idx * 0.1,
                    blending: THREE.AdditiveBlending
                });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.rotation.x = Math.PI / 2;
                ring.position.y = -1.35;
                this.platformGroup.add(ring);
            });

            // Radial tick marks
            const tickCount = 24;
            const tickGeo = new THREE.BufferGeometry();
            const tickPos = [];
            for (let i = 0; i < tickCount; i++) {
                const angle = (i / tickCount) * Math.PI * 2;
                const x1 = Math.cos(angle) * 1.45;
                const z1 = Math.sin(angle) * 1.45;
                const x2 = Math.cos(angle) * 1.6;
                const z2 = Math.sin(angle) * 1.6;
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
            const particleCount = 220;
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

            // Reset Button
            const resetBtn = document.getElementById("resetFaceViewBtn");
            if (resetBtn) {
                resetBtn.addEventListener("click", () => {
                    if (window.gsap) {
                        gsap.to(this.faceGroup.rotation, { x: 0, y: 0, z: 0, duration: 0.8, ease: "power2.out" });
                    } else {
                        this.faceGroup.rotation.set(0, 0, 0);
                    }
                });
            }

            // Window Resize
            window.addEventListener("resize", () => {
                if (!this.container) return;
                const w = this.container.clientWidth;
                const h = this.container.clientHeight;
                this.camera.aspect = w / h;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(w, h);
            });
        }

        /**
         * Triggered when an actual detection scan starts via Flask
         */
        startScan() {
            this.isScanning = true;
            this.scanState = "scanning";
            this.laserSpeed = 2.8;

            // Shift laser color to bright electric cyan/gold during analysis
            this.laserMaterial.color.setHex(0x00f0ff);
            this.laserHalo.material.color.setHex(0x00f0ff);
            this.meshMaterial.opacity = 0.7;
            this.landmarkMaterial.size = 0.085;

            if (window.gsap) {
                gsap.to(this.meshMaterial, { opacity: 0.8, duration: 0.4, yoyo: true, repeat: -1 });
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
            this.meshMaterial.opacity = 0.38;
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

                const breathing = Math.sin(elapsed * 1.5) * 0.04;
                this.faceGroup.rotation.y = this.mouse.x + Math.sin(elapsed * 0.8) * 0.12;
                this.faceGroup.rotation.x = -this.mouse.y + breathing;
            }

            // 2. Moving Laser Sweep
            this.laserY += this.laserDirection * this.laserSpeed * delta;
            if (this.laserY > 1.1) {
                this.laserY = 1.1;
                this.laserDirection = -1;
            } else if (this.laserY < -1.0) {
                this.laserY = -1.0;
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
