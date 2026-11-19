"""
FACEGUARD AI - Enterprise Deepfake Detection & Facial Forensics Platform
Module: app.py
Purpose: Main WSGI Application Entrypoint for Gunicorn, Render, and Local Development
"""
import os
from faceguard import create_app
from faceguard.config import DevelopmentConfig, ProductionConfig

# Determine execution environment (defaults to ProductionConfig for security)
env = os.environ.get("FLASK_ENV", "production").lower()
config_class = DevelopmentConfig if env == "development" else ProductionConfig

# Instantiate application factory
app = create_app(config_class)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Host on 0.0.0.0 for containerized and network access
    app.run(host="0.0.0.0", port=port, debug=(env == "development"))
