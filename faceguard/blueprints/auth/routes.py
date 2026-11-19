"""
FACEGUARD AI - Authentication Routes
Module: faceguard/blueprints/auth/routes.py
"""
from datetime import datetime, timezone, timedelta
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from faceguard.blueprints.auth import auth_bp
from faceguard.blueprints.auth.forms import (
    LoginForm, RegistrationForm, VerifyEmailForm,
    ForgotPasswordForm, ResetPasswordForm,
    UpdateProfileForm, ChangePasswordForm
)
from faceguard.extensions import db
from faceguard.models.user import User, get_utc_now
from faceguard.utils.mailer import send_otp_email, send_reset_password_email
from faceguard.utils.security import log_audit

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticates existing users and routes unverified users to OTP verification"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            log_audit("failed_login_attempt", f"Attempted Email: {email}")
            flash("Invalid email address or password. Please try again.", "error")
            return render_template("login.html", form=form)

        # Check Email Verification Status
        if not user.is_verified:
            otp = user.generate_otp()
            db.session.commit()
            sent, msg = send_otp_email(user.email, otp, user.full_name)
            if sent:
                flash("Please verify your email address to continue. We sent a 6-digit code to your inbox.", "warning")
            else:
                flash(f"Please verify your email. Verification code: {otp}", "info")
            return redirect(url_for("auth.verify_email", email=user.email))

        # Successful Login
        login_user(user, remember=form.remember_me.data)
        user.last_login = get_utc_now()
        db.session.commit()
        log_audit("user_login", f"Successful login for {user.email}", user_id=user.id)

        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.overview"))

    return render_template("login.html", form=form)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registers a new user and triggers 6-digit OTP verification email"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        full_name = form.full_name.data.strip()
        password = form.password.data

        # Check if an unverified user exists with this email
        user = User.query.filter_by(email=email).first()
        if user and not user.is_verified:
            user.full_name = full_name
            user.set_password(password)
        else:
            user = User(
                full_name=full_name,
                email=email,
                role="admin" if "admin" in email else "user",
                is_verified=False
            )
            user.set_password(password)
            db.session.add(user)

        otp = user.generate_otp()
        db.session.commit()

        # Send verification email
        sent, msg = send_otp_email(email, otp, full_name)
        log_audit("user_registered", f"Registration initiated for {email}", user_id=user.id)

        if sent:
            flash("Account created! We sent a 6-digit verification code to your email.", "success")
        else:
            flash(f"Account created! Your 6-digit verification code is: {otp}", "info")

        return redirect(url_for("auth.verify_email", email=email))

    return render_template("register.html", form=form)

@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    """Verifies user email using 6-digit OTP with 5-minute expiry and rate-limiting"""
    email = request.args.get("email", "").strip().lower()
    if not email:
        flash("Email address required for verification.", "error")
        return redirect(url_for("auth.register"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Account not found. Please register.", "error")
        return redirect(url_for("auth.register"))

    if user.is_verified:
        flash("Your email is already verified. Please sign in.", "info")
        return redirect(url_for("auth.login"))

    form = VerifyEmailForm()
    if form.validate_on_submit():
        code = form.otp_code.data.strip()
        success, message = user.verify_otp(code)

        if not success:
            db.session.commit()
            log_audit("failed_otp_verification", f"Failed OTP for {email}")
            flash(message, "error")
            return render_template("verify_email.html", form=form, email=email)

        # Verification Succeeded
        db.session.commit()
        login_user(user)
        log_audit("email_verified", f"Email verified successfully for {email}", user_id=user.id)
        flash("Email verified successfully! Welcome to FACEGUARD AI.", "success")
        return redirect(url_for("dashboard.overview"))

    return render_template("verify_email.html", form=form, email=email)

@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    """Resends a fresh 6-digit OTP with a new 5-minute expiration"""
    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Account not found.", "error")
        return redirect(url_for("auth.register"))

    if user.is_verified:
        flash("Your account is already verified. Please sign in.", "info")
        return redirect(url_for("auth.login"))

    otp = user.generate_otp()
    db.session.commit()

    sent, msg = send_otp_email(email, otp, user.full_name)
    log_audit("otp_resend", f"New OTP sent to {email}", user_id=user.id)

    if sent:
        flash("A fresh verification code has been delivered to your email.", "success")
    else:
        flash(f"New verification code: {otp}", "info")

    return redirect(url_for("auth.verify_email", email=email))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Initiates password reset by issuing a 6-digit verification code"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            import random
            reset_code = f"{random.randint(100000, 999999)}"
            user.reset_token = reset_code
            user.reset_expiry = get_utc_now() + timedelta(minutes=5)
            db.session.commit()

            sent, msg = send_reset_password_email(email, reset_code, user.full_name)
            log_audit("password_reset_requested", f"Reset token issued for {email}", user_id=user.id)

            if sent:
                flash("A 6-digit reset code has been delivered to your email.", "success")
            else:
                flash(f"Password reset code: {reset_code}", "info")
        else:
            # Prevent email enumeration by flashing generic message
            flash("If an account exists with this email address, a reset code has been sent.", "info")

        return redirect(url_for("auth.reset_password", email=email))

    return render_template("forgot_password.html", form=form)

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Verifies reset code and updates password"""
    email = request.args.get("email", "").strip().lower()
    form = ResetPasswordForm()

    if form.validate_on_submit():
        code = form.otp_code.data.strip()
        new_password = form.new_password.data
        user = User.query.filter_by(email=email).first()

        if not user or not user.reset_token or not user.reset_expiry:
            flash("Invalid or expired password reset request. Please request a new code.", "error")
            return redirect(url_for("auth.forgot_password"))

        now = get_utc_now()
        expiry = user.reset_expiry if user.reset_expiry.tzinfo else user.reset_expiry.replace(tzinfo=timezone.utc)
        if now > expiry:
            flash("Reset code has expired. Please request a new one.", "error")
            return redirect(url_for("auth.forgot_password"))

        if user.reset_token.strip() != code:
            flash("Incorrect reset code. Please try again.", "error")
            return render_template("reset_password.html", form=form, email=email)

        # Update password
        user.set_password(new_password)
        user.reset_token = None
        user.reset_expiry = None
        db.session.commit()

        log_audit("password_reset_completed", f"Password changed for {email}", user_id=user.id)
        flash("Password has been reset successfully! You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", form=form, email=email)

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile management and account statistics"""
    profile_form = UpdateProfileForm(prefix="profile")
    password_form = ChangePasswordForm(prefix="password")

    if profile_form.validate_on_submit() and profile_form.submit.data:
        current_user.full_name = profile_form.full_name.data.strip()
        db.session.commit()
        log_audit("profile_updated", f"Updated name to {current_user.full_name}")
        flash("Your profile details have been saved.", "success")
        return redirect(url_for("auth.profile"))

    if password_form.validate_on_submit() and password_form.submit.data:
        if not current_user.check_password(password_form.current_password.data):
            flash("Incorrect current password.", "error")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            log_audit("password_changed", "User updated account password")
            flash("Password updated successfully.", "success")
            return redirect(url_for("auth.profile"))

    # Populate current name
    if request.method == "GET":
        profile_form.full_name.data = current_user.full_name

    # Account metrics
    total_scans = current_user.scans.count()
    real_scans = current_user.scans.filter_by(overall_prediction="REAL").count()
    fake_scans = current_user.scans.filter_by(overall_prediction="FAKE").count()

    return render_template(
        "profile.html",
        user=current_user,
        profile_form=profile_form,
        password_form=password_form,
        total_scans=total_scans,
        real_scans=real_scans,
        fake_scans=fake_scans
    )

@auth_bp.route("/logout")
@login_required
def logout():
    """Terminates session securely"""
    log_audit("user_logout", f"User {current_user.email} signed out", user_id=current_user.id)
    logout_user()
    flash("You have been securely signed out.", "info")
    return redirect(url_for("auth.login"))
