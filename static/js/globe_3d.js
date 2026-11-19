/**
 * FACEGUARD AI - Interactive 3D Digital Holographic Globe
 * Module: static/js/globe_3d.js
 * Powered by Three.js (r128) & GSAP (3.12.5)
 * 
 * Features:
 * - Spherical digital Earth with procedural cyber continent coordinates
 * - Cyan and electric blue longitude/latitude wireframe grid
 * - Glowing atmospheric envelope & orbital rings
 * - Arcing great-circle telemetry lines between global security hubs
 * - Pulsating holographic nodes and traveling photon packets
 * - Interactive mouse drag rotation & wheel zoom with momentum damping
 */

(function () {
    "use strict";

    class HolographicGlobe {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            if (!this.container) return;

            this.scene = null;
            this.camera = null;
            this.renderer = null;
            this.clock = new THREE.Clock();

            // Groups
            this.globeGroup = new THREE.Group();
            this.atmosphereGroup = new THREE.Group();
            this.orbitalGroup = new THREE.Group();
            this.arcsGroup = new THREE.Group();
            this.photonPackets = [];

            // Interaction
            this.isDragging = false;
            this.previousMousePosition = { x: 0, y: 0 };
            this.rotationVelocity = { x: 0, y: 0.003 };
            this.targetZoom = 4.2;

            this.init();
        }

        init() {
            const width = this.container.clientWidth || 500;
            const height = this.container.clientHeight || 380;

            // 1. Scene
            this.scene = new THREE.Scene();

            // 2. Camera
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            this.camera.position.set(0, 0, this.targetZoom);

            // 3. Renderer
            this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.container.appendChild(this.renderer.domElement);

            // 4. Lighting
            const ambient = new THREE.AmbientLight(0x00f0ff, 0.6);
            this.scene.add(ambient);

            const dirLight = new THREE.DirectionalLight(0x38bdf8, 2.0);
            dirLight.position.set(5, 3, 5);
            this.scene.add(dirLight);

            const backLight = new THREE.PointLight(0xa855f7, 2.5, 10);
            backLight.position.set(-4, -2, -3);
            this.scene.add(backLight);

            // 5. Build Globe Entities
            this.buildCoreSphere();
            this.buildGridLines();
            this.buildAtmosphere();
            this.buildGlobalNodesAndArcs();
            this.buildOrbitalRings();

            this.scene.add(this.globeGroup);

            // 6. Bind User Controls
            this.bindEvents();

            // 7. Start Animation Loop
            this.animate = this.animate.bind(this);
            requestAnimationFrame(this.animate);
        }

        /**
         * Core Sphere with Continental Point Cloud
         */
        buildCoreSphere() {
            const radius = 1.35;

            // Inner dark globe
            const sphereGeo = new THREE.SphereGeometry(radius * 0.99, 48, 48);
            const sphereMat = new THREE.MeshBasicMaterial({
                color: 0x050a18,
                transparent: true,
                opacity: 0.88
            });
            const innerSphere = new THREE.Mesh(sphereGeo, sphereMat);
            this.globeGroup.add(innerSphere);

            // Procedural Continents Point Cloud (Fibonacci Sphere mapping with landmass density filter)
            const dotCount = 1800;
            const dotPositions = [];
            const dotColors = [];
            const baseColor = new THREE.Color(0x00f0ff);
            const accentColor = new THREE.Color(0x3b82f6);

            for (let i = 0; i < dotCount; i++) {
                const phi = Math.acos(-1 + (2 * i) / dotCount);
                const theta = Math.sqrt(dotCount * Math.PI) * phi;

                // Spherical to Cartesian
                let x = Math.cos(theta) * Math.sin(phi);
                let y = Math.sin(theta) * Math.sin(phi);
                let z = Math.cos(phi);

                // Approximate landmass mask using spherical harmonics
                const lat = (Math.PI / 2 - phi) * (180 / Math.PI);
                const lon = (theta % (Math.PI * 2)) * (180 / Math.PI) - 180;

                const isLand = this.isApproxLand(lat, lon);
                if (isLand) {
                    const r = radius * 1.01;
                    dotPositions.push(x * r, y * r, z * r);

                    const mixed = baseColor.clone().lerp(accentColor, Math.random() * 0.4);
                    dotColors.push(mixed.r, mixed.g, mixed.b);
                }
            }

            const pointsGeo = new THREE.BufferGeometry();
            pointsGeo.setAttribute("position", new THREE.Float32BufferAttribute(dotPositions, 3));
            pointsGeo.setAttribute("color", new THREE.Float32BufferAttribute(dotColors, 3));

            const pointsMat = new THREE.PointsMaterial({
                size: 0.038,
                vertexColors: true,
                transparent: true,
                opacity: 0.95,
                blending: THREE.AdditiveBlending
            });

            this.continentPoints = new THREE.Points(pointsGeo, pointsMat);
            this.globeGroup.add(this.continentPoints);
        }

        /**
         * Heuristic landmass approximation for major continental masses
         */
        isApproxLand(lat, lon) {
            // North America
            if (lat > 15 && lat < 70 && lon > -165 && lon < -55) return true;
            // South America
            if (lat > -55 && lat < 12 && lon > -82 && lon < -35) return true;
            // Eurasia
            if (lat > 10 && lat < 75 && lon > -10 && lon < 150) return true;
            // Africa
            if (lat > -35 && lat < 37 && lon > -18 && lon < 52) return true;
            // Australia & Oceania
            if (lat > -45 && lat < -10 && lon > 110 && lon < 178) return true;
            // Antarctica
            if (lat < -65) return true;
            // Random maritime island clusters
            return Math.sin(lat * 0.2) * Math.cos(lon * 0.2) > 0.65;
        }

        /**
         * Longitudinal & Latitudinal Cyber Wireframe Grid
         */
        buildGridLines() {
            const radius = 1.35;
            const gridGeo = new THREE.SphereGeometry(radius, 18, 12);
            const gridMat = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                wireframe: true,
                transparent: true,
                opacity: 0.12,
                blending: THREE.AdditiveBlending
            });
            const gridMesh = new THREE.Mesh(gridGeo, gridMat);
            this.globeGroup.add(gridMesh);
        }

        /**
         * Glowing Atmospheric Envelope
         */
        buildAtmosphere() {
            const radius = 1.35;
            const atmoGeo = new THREE.SphereGeometry(radius * 1.15, 32, 32);
            const atmoMat = new THREE.MeshBasicMaterial({
                color: 0x38bdf8,
                side: THREE.BackSide,
                transparent: true,
                opacity: 0.15,
                blending: THREE.AdditiveBlending
            });
            const atmoMesh = new THREE.Mesh(atmoGeo, atmoMat);
            this.atmosphereGroup.add(atmoMesh);
            this.scene.add(this.atmosphereGroup);
        }

        /**
         * Global Security Hub Nodes & Great-Circle Telemetry Arcs
         */
        buildGlobalNodesAndArcs() {
            // Major Global Digital Forensics & Defense Hubs (Lat, Long, Name)
            const hubs = [
                { lat: 28.61, lon: 77.20, name: "New Delhi" },
                { lat: 37.77, lon: -122.41, name: "San Francisco" },
                { lat: 51.50, lon: -0.12, name: "London" },
                { lat: 35.67, lon: 139.65, name: "Tokyo" },
                { lat: 1.35, lon: 103.81, name: "Singapore" },
                { lat: 50.11, lon: 8.68, name: "Frankfurt" },
                { lat: -33.86, lon: 151.20, name: "Sydney" }
            ];

            const radius = 1.35;
            const nodePositions = [];

            hubs.forEach(hub => {
                const pos = this.latLonToVector3(hub.lat, hub.lon, radius * 1.01);
                nodePositions.push(pos.x, pos.y, pos.z);
            });

            // Pulsating Nodes
            const nodeGeo = new THREE.BufferGeometry();
            nodeGeo.setAttribute("position", new THREE.Float32BufferAttribute(nodePositions, 3));
            const nodeMat = new THREE.PointsMaterial({
                color: 0x10b981,
                size: 0.08,
                transparent: true,
                opacity: 0.95,
                blending: THREE.AdditiveBlending
            });
            const nodePoints = new THREE.Points(nodeGeo, nodeMat);
            this.globeGroup.add(nodePoints);

            // Great-Circle Arcs between selected security pairs
            const connections = [
                [0, 1], // New Delhi -> San Francisco
                [0, 2], // New Delhi -> London
                [0, 3], // New Delhi -> Tokyo
                [0, 4], // New Delhi -> Singapore
                [2, 5], // London -> Frankfurt
                [1, 3], // San Francisco -> Tokyo
                [4, 6]  // Singapore -> Sydney
            ];

            connections.forEach(conn => {
                const p1 = this.latLonToVector3(hubs[conn[0]].lat, hubs[conn[0]].lon, radius);
                const p2 = this.latLonToVector3(hubs[conn[1]].lat, hubs[conn[1]].lon, radius);

                // Compute high-altitude midpoint for curved parabolic arc
                const mid = p1.clone().add(p2).multiplyScalar(0.5);
                const dist = p1.distanceTo(p2);
                mid.normalize().multiplyScalar(radius + dist * 0.28);

                const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
                const curvePoints = curve.getPoints(40);
                const curveGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
                const curveMat = new THREE.LineBasicMaterial({
                    color: 0x00f0ff,
                    transparent: true,
                    opacity: 0.35,
                    blending: THREE.AdditiveBlending
                });
                const line = new THREE.Line(curveGeo, curveMat);
                this.arcsGroup.add(line);

                // Photon Packet (Traveling particle)
                this.photonPackets.push({
                    curve: curve,
                    progress: Math.random(),
                    speed: 0.25 + Math.random() * 0.35,
                    mesh: null
                });
            });

            // Create geometry for all photon packets
            const packetGeo = new THREE.BufferGeometry();
            const packetPositions = new Float32Array(this.photonPackets.length * 3);
            packetGeo.setAttribute("position", new THREE.BufferAttribute(packetPositions, 3));
            const packetMat = new THREE.PointsMaterial({
                color: 0x00f0ff,
                size: 0.07,
                transparent: true,
                opacity: 1.0,
                blending: THREE.AdditiveBlending
            });
            this.packetsMesh = new THREE.Points(packetGeo, packetMat);
            this.arcsGroup.add(this.packetsMesh);

            this.globeGroup.add(this.arcsGroup);
        }

        latLonToVector3(lat, lon, radius) {
            const phi = (90 - lat) * (Math.PI / 180);
            const theta = (lon + 180) * (Math.PI / 180);
            const x = -(radius * Math.sin(phi) * Math.cos(theta));
            const z = radius * Math.sin(phi) * Math.sin(theta);
            const y = radius * Math.cos(phi);
            return new THREE.Vector3(x, y, z);
        }

        /**
         * Animated Tilted Orbital Rings
         */
        buildOrbitalRings() {
            const ringColors = [0x00f0ff, 0xa855f7];
            const radii = [2.05, 2.35];

            radii.forEach((r, idx) => {
                const ringGeo = new THREE.RingGeometry(r - 0.015, r, 64);
                const ringMat = new THREE.MeshBasicMaterial({
                    color: ringColors[idx],
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.4 - idx * 0.15,
                    blending: THREE.AdditiveBlending
                });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.rotation.x = Math.PI / 3 + idx * 0.3;
                ring.rotation.y = idx * 0.4;
                this.orbitalGroup.add(ring);
            });

            this.scene.add(this.orbitalGroup);
        }

        /**
         * Mouse Drag Orbiting & Scroll Zoom
         */
        bindEvents() {
            const el = this.container;

            el.addEventListener("mousedown", (e) => {
                this.isDragging = true;
                this.previousMousePosition = { x: e.clientX, y: e.clientY };
            });

            window.addEventListener("mouseup", () => {
                this.isDragging = false;
            });

            el.addEventListener("mousemove", (e) => {
                if (!this.isDragging) return;

                const deltaX = e.clientX - this.previousMousePosition.x;
                const deltaY = e.clientY - this.previousMousePosition.y;

                this.rotationVelocity.x = deltaY * 0.005;
                this.rotationVelocity.y = deltaX * 0.005;

                this.globeGroup.rotation.y += this.rotationVelocity.y;
                this.globeGroup.rotation.x += this.rotationVelocity.x;

                this.previousMousePosition = { x: e.clientX, y: e.clientY };
            });

            // Wheel Zoom (Clamped)
            el.addEventListener("wheel", (e) => {
                e.preventDefault();
                this.targetZoom += e.deltaY * 0.003;
                this.targetZoom = Math.max(2.6, Math.min(6.5, this.targetZoom));
            }, { passive: false });

            // Reset Button
            const resetBtn = document.getElementById("resetGlobeViewBtn");
            if (resetBtn) {
                resetBtn.addEventListener("click", () => {
                    this.targetZoom = 4.2;
                    if (window.gsap) {
                        gsap.to(this.globeGroup.rotation, { x: 0, y: 0, z: 0, duration: 1.0, ease: "power2.out" });
                        gsap.to(this.camera.position, { z: 4.2, duration: 1.0, ease: "power2.out" });
                    } else {
                        this.globeGroup.rotation.set(0, 0, 0);
                        this.camera.position.z = 4.2;
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
         * Main Render Loop
         */
        animate() {
            requestAnimationFrame(this.animate);
            const delta = this.clock.getDelta();

            // 1. Idle rotation with inertia
            if (!this.isDragging) {
                this.globeGroup.rotation.y += 0.004;
                this.rotationVelocity.x *= 0.95;
                this.rotationVelocity.y *= 0.95;
                this.globeGroup.rotation.x += this.rotationVelocity.x;
            }

            // 2. Orbital rings counter-rotation
            this.orbitalGroup.rotation.z += 0.003;
            this.orbitalGroup.rotation.y += 0.002;

            // 3. Smooth Camera Zoom
            this.camera.position.z += (this.targetZoom - this.camera.position.z) * 0.1;

            // 4. Update Traveling Photon Packets along Arcs
            if (this.packetsMesh && this.photonPackets.length > 0) {
                const pos = this.packetsMesh.geometry.attributes.position.array;
                for (let i = 0; i < this.photonPackets.length; i++) {
                    const pkt = this.photonPackets[i];
                    pkt.progress += pkt.speed * delta;
                    if (pkt.progress > 1.0) pkt.progress = 0;

                    const point = pkt.curve.getPoint(pkt.progress);
                    pos[i * 3] = point.x;
                    pos[i * 3 + 1] = point.y;
                    pos[i * 3 + 2] = point.z;
                }
                this.packetsMesh.geometry.attributes.position.needsUpdate = true;
            }

            this.renderer.render(this.scene, this.camera);
        }
    }

    // Initialize globally when DOM is ready
    window.addEventListener("DOMContentLoaded", function () {
        if (typeof THREE !== "undefined" && document.getElementById("globe3DContainer")) {
            window.HolographicGlobe = new HolographicGlobe("globe3DContainer");
        }
    });

})();
