"""
FACEGUARD AI - Shared Application Extensions
Module: faceguard/extensions.py
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Database ORM instance
db = SQLAlchemy()

# Authentication & Session Manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access FACEGUARD AI."
login_manager.login_message_category = "warning"

# CSRF Protection
csrf = CSRFProtect()
