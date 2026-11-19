"""
FACEGUARD AI - Authentication Forms (WTForms)
Module: faceguard/blueprints/auth/forms.py
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from faceguard.models.user import User

class LoginForm(FlaskForm):
    email = StringField(
        "Email Address",
        validators=[DataRequired(message="Please provide your email address."), Email(message="Please enter a valid email.")]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please provide your password.")]
    )
    remember_me = BooleanField("Remember this device")
    submit = SubmitField("Sign In")

class RegistrationForm(FlaskForm):
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(message="Please enter your full name."), Length(min=2, max=100)]
    )
    email = StringField(
        "Email Address",
        validators=[DataRequired(message="Please enter a valid email address."), Email(message="Please enter a valid email address.")]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required."), Length(min=8, message="Password must be at least 8 characters long.")]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(message="Please confirm your password."), EqualTo("password", message="Passwords do not match.")]
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing and existing.is_verified:
            raise ValidationError("An account with this email address already exists. Please log in.")

class VerifyEmailForm(FlaskForm):
    otp_code = StringField(
        "6-Digit Verification Code",
        validators=[
            DataRequired(message="Please enter the 6-digit verification code."),
            Length(min=6, max=6, message="The code must be exactly 6 digits.")
        ]
    )
    submit = SubmitField("Verify Email")

class ForgotPasswordForm(FlaskForm):
    email = StringField(
        "Registered Email Address",
        validators=[DataRequired(message="Please enter your registered email address."), Email(message="Please enter a valid email.")]
    )
    submit = SubmitField("Send Reset Code")

class ResetPasswordForm(FlaskForm):
    otp_code = StringField(
        "6-Digit Reset Code",
        validators=[
            DataRequired(message="Please enter the 6-digit reset code."),
            Length(min=6, max=6, message="The code must be exactly 6 digits.")
        ]
    )
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(message="New password is required."), Length(min=8, message="Password must be at least 8 characters long.")]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(message="Please confirm your new password."), EqualTo("new_password", message="Passwords do not match.")]
    )
    submit = SubmitField("Reset Password")

class UpdateProfileForm(FlaskForm):
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(message="Full name cannot be empty."), Length(min=2, max=100)]
    )
    submit = SubmitField("Save Profile")

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Please enter your current password.")]
    )
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(message="New password is required."), Length(min=8, message="New password must be at least 8 characters long.")]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(message="Please confirm your new password."), EqualTo("new_password", message="Passwords do not match.")]
    )
    submit = SubmitField("Update Password")
