/**
 * FACEGUARD AI - Advanced Cyber Animation & Micro-Interactions Engine
 * Module: static/js/cyber_animations.js
 * Powered by GSAP (3.12.5) & Modern Web Animations API
 * 
 * Features:
 * - Cinematic Dashboard Entrance Timeline
 * - 3D Perspective Card Tilt on Mouse Hover
 * - Magnetic Pull Micro-Interaction for Buttons & Quick Actions
 * - Global Keyboard Shortcut (CTRL+K for Cyber Search)
 * - Ripple effects on interactive elements
 * - Reduced-Motion Accessibility Compliance
 */

(function () {
    "use strict";

    // 1. Accessibility Check
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    document.addEventListener("DOMContentLoaded", function () {
        // Run Cinematic Entrance if GSAP is available and motion is enabled
        if (window.gsap && !prefersReducedMotion) {
            initCinematicEntrance();
            initCard3DTilt();
            initMagneticButtons();
        }

        initCyberSearchShortcut();
    });

    /**
     * Cinematic Staggered Entrance Animation
     */
    function initCinematicEntrance() {
        const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

        // Step 1: Top KPI Cards slide in & scale
        tl.from(".kpi-stat-card", {
            duration: 0.75,
            y: 28,
            opacity: 0,
            stagger: 0.08,
            scale: 0.96
        })
        // Step 2: 3D Viewport Stages expand with holographic fade
        .from(".scanner-viewport-card, .scanner-analysis-card", {
            duration: 0.85,
            y: 35,
            opacity: 0,
            stagger: 0.12
        }, "-=0.4")
        // Step 3: Globe & Threat Analytics
        .from(".globe-viewport-card, .threat-overview-card", {
            duration: 0.85,
            y: 35,
            opacity: 0,
            stagger: 0.12
        }, "-=0.5")
        // Step 4: Risk Dial & Quick Actions
        .from(".risk-gauge-card, .quick-action-card", {
            duration: 0.7,
            y: 25,
            opacity: 0,
            stagger: 0.06
        }, "-=0.5")
        // Step 5: Recent Scans & System Overview
        .from(".cyber-table tr, .system-indicator-bar", {
            duration: 0.6,
            opacity: 0,
            stagger: 0.04
        }, "-=0.4");
    }

    /**
     * 3D Perspective Card Tilt
     */
    function initCard3DTilt() {
        const tiltCards = document.querySelectorAll(".kpi-stat-card, .quick-action-card, .cyber-card");

        tiltCards.forEach(card => {
            // Avoid tilting interactive 3D viewports directly
            if (card.classList.contains("scanner-viewport-card") || card.classList.contains("globe-viewport-card")) {
                return;
            }

            card.style.transformStyle = "preserve-3d";

            card.addEventListener("mousemove", (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const centerX = rect.width / 2;
                const centerY = rect.height / 2;

                const rotateX = ((y - centerY) / centerY) * -6; // max -6deg to +6deg
                const rotateY = ((x - centerX) / centerX) * 6;  // max -6deg to +6deg

                gsap.to(card, {
                    rotationX: rotateX,
                    rotationY: rotateY,
                    transformPerspective: 900,
                    scale: 1.015,
                    duration: 0.35,
                    ease: "power1.out"
                });
            });

            card.addEventListener("mouseleave", () => {
                gsap.to(card, {
                    rotationX: 0,
                    rotationY: 0,
                    scale: 1,
                    duration: 0.6,
                    ease: "power2.out"
                });
            });
        });
    }

    /**
     * Magnetic Button Pull Micro-Interactions
     */
    function initMagneticButtons() {
        const magneticBtns = document.querySelectorAll(".btn-primary, .theme-toggle-btn, .notification-bell-btn");

        magneticBtns.forEach(btn => {
            btn.addEventListener("mousemove", (e) => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;

                gsap.to(btn, {
                    x: x * 0.28,
                    y: y * 0.28,
                    duration: 0.25,
                    ease: "power2.out"
                });
            });

            btn.addEventListener("mouseleave", () => {
                gsap.to(btn, {
                    x: 0,
                    y: 0,
                    duration: 0.5,
                    ease: "elastic.out(1, 0.4)"
                });
            });
        });
    }

    /**
     * Cyber Search Shortcut (CTRL+K or CMD+K)
     */
    function initCyberSearchShortcut() {
        const searchInput = document.getElementById("cyberSearchInput");
        if (!searchInput) return;

        window.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
                if (window.gsap) {
                    gsap.fromTo(searchInput.parentElement, { scale: 0.98 }, { scale: 1.03, duration: 0.3, yoyo: true, repeat: 1 });
                }
            }
        });
    }

})();
