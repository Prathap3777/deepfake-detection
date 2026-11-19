"""
Module: app.py
Purpose: Flask Web Application Backend with Complete Authentication & Deepfake Detection Engine
"""
import os
import uuid
import random
import functools
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

# Local modules
import gc
from database import (
    init_db, get_user_by_email, get_user_by_id, create_user,
    update_user_otp, increment_otp_attempts, activate_user,
    set_reset_token, update_password
)
from mailer import send_otp_email, send_reset_password_email, is_smtp_configured

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "deepfake-auth-secret-key-2026-production")
app.permanent_session_lifetime = timedelta(days=7)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize SQLite database on startup
init_db()

# Lazy-loaded inference engine (keeps startup memory under 50MB for Render free tier)
_predictor = None

def get_predictor():
    global _predictor
    if _predictor is None:
        print("[*] Loading Deepfake Detection Inference Engine...")
        from predict import DeepfakePredictor
        _predictor = DeepfakePredictor()
        print("[✓] Inference Engine loaded successfully.")
    return _predictor

def allowed_file(filename):
    """Validates allowed image file extensions"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# Authentication Decorator
# ==========================================
def login_required(view):
    """Protects routes from unauthenticated access"""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('user_id'):
            flash("Please log in to access the Deepfake Detection Dashboard.", "warning")
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# ==========================================
# Authentication Routes
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Renders login page and authenticates users"""
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me')

        if not email or not password:
            flash("Please provide both email address and password.", "error")
            return render_template('login.html')

        user = get_user_by_email(email)

        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid email address or password. Please try again.", "error")
            return render_template('login.html')

        # Check email verification status
        if user['is_verified'] == 0:
            flash("Your email is not verified yet. A verification code has been sent to your email.", "warning")
            return redirect(url_for('verify_email', email=user['email']))

        # Set authenticated session
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_email'] = user['email']
        session.permanent = bool(remember_me)

        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Renders registration page and creates new user account with OTP"""
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template('register.html')

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html')

        existing_user = get_user_by_email(email)
        if existing_user:
            if existing_user['is_verified'] == 1:
                flash("An account with this email address already exists. Please log in.", "error")
                return redirect(url_for('login'))
            else:
                otp_code = f"{random.randint(100000, 999999)}"
                otp_expiry = datetime.now() + timedelta(minutes=5)
                update_user_otp(email, otp_code, otp_expiry)
                send_otp_email(email, otp_code, full_name)
                flash("A fresh verification code has been sent to your email.", "info")
                return redirect(url_for('verify_email', email=email))

        # Generate 6-digit OTP with 5 minutes expiry
        otp_code = f"{random.randint(100000, 999999)}"
        otp_expiry = datetime.now() + timedelta(minutes=5)
        password_hash = generate_password_hash(password)

        success, msg = create_user(full_name, email, password_hash, otp_code, otp_expiry)
        if not success:
            flash(msg, "error")
            return render_template('register.html')

        # Send OTP email
        mail_sent, mail_msg = send_otp_email(email, otp_code, full_name)
        if not mail_sent:
            flash(f"Account created! Your 6-digit verification code is: {otp_code}", "info")
        else:
            flash("Account created! We sent a 6-digit verification code to your email.", "success")

        return redirect(url_for('verify_email', email=email))

    return render_template('register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Validates 6-digit OTP code and activates user account"""
    email = request.args.get('email', '') or request.form.get('email', '')
    email = email.strip().lower()

    if not email:
        flash("Email address is required to verify account.", "error")
        return redirect(url_for('register'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp_code', '').strip()

        if not entered_otp or len(entered_otp) != 6:
            flash("Please enter a valid 6-digit verification code.", "error")
            return render_template('verify_email.html', email=email)

        user = get_user_by_email(email)
        if not user:
            flash("Account not found. Please register first.", "error")
            return redirect(url_for('register'))

        if user['is_verified'] == 1:
            flash("Your account is already verified. Please log in.", "info")
            return redirect(url_for('login'))

        if user['otp_attempts'] >= 5:
            flash("Too many failed attempts. Please request a new verification code.", "error")
            return render_template('verify_email.html', email=email)

        if not user['otp_expiry']:
            flash("Verification code has expired. Please request a new code.", "error")
            return render_template('verify_email.html', email=email)

        try:
            expiry_dt = datetime.fromisoformat(str(user['otp_expiry']))
        except Exception:
            expiry_dt = datetime.now() - timedelta(seconds=1)

        if datetime.now() > expiry_dt:
            flash("Verification code has expired. Please click Resend Code.", "error")
            return render_template('verify_email.html', email=email)

        if user['otp_code'] != entered_otp:
            increment_otp_attempts(email)
            remaining = 5 - (user['otp_attempts'] + 1)
            flash(f"Incorrect verification code. ({remaining} attempts remaining)", "error")
            return render_template('verify_email.html', email=email)

        activate_user(email)
        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('verify_email.html', email=email)

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resends a new 6-digit OTP code with fresh 5-minute expiry"""
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash("Email address required.", "error")
        return redirect(url_for('register'))

    user = get_user_by_email(email)
    if not user:
        flash("Account not found.", "error")
        return redirect(url_for('register'))

    if user['is_verified'] == 1:
        flash("Your account is already verified. Please log in.", "info")
        return redirect(url_for('login'))

    new_otp = f"{random.randint(100000, 999999)}"
    new_expiry = datetime.now() + timedelta(minutes=5)
    update_user_otp(email, new_otp, new_expiry)

    sent, msg = send_otp_email(email, new_otp, user['full_name'])
    if sent:
        flash("A new 6-digit verification code has been sent to your email.", "success")
    else:
        flash(f"New verification code: {new_otp} (Enter this code below)", "info")

    return redirect(url_for('verify_email', email=email))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handles forgot password requests and sends 6-digit reset code"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash("Please enter your registered email address.", "error")
            return render_template('forgot_password.html')

        user = get_user_by_email(email)
        if not user:
            # For security, avoid disclosing whether an email exists
            flash("If an account exists with this email, a reset code has been sent.", "info")
            return redirect(url_for('reset_password', email=email))

        reset_code = f"{random.randint(100000, 999999)}"
        reset_expiry = datetime.now() + timedelta(minutes=5)
        set_reset_token(email, reset_code, reset_expiry)

        sent, msg = send_reset_password_email(email, reset_code, user['full_name'])
        if sent:
            flash("A 6-digit password reset code has been sent to your email.", "success")
        else:
            flash(f"Password reset code: {reset_code} (Enter this code below to proceed)", "info")

        return redirect(url_for('reset_password', email=email))

    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Validates reset code and updates password"""
    email = request.args.get('email', '') or request.form.get('email', '')
    email = email.strip().lower()

    if request.method == 'POST':
        reset_token = request.form.get('reset_token', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_new_password = request.form.get('confirm_new_password', '')

        if not reset_token or not new_password or not confirm_new_password:
            flash("All fields are required.", "error")
            return render_template('reset_password.html', email=email)

        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template('reset_password.html', email=email)

        if new_password != confirm_new_password:
            flash("Passwords do not match.", "error")
            return render_template('reset_password.html', email=email)

        user = get_user_by_email(email)
        if not user:
            flash("Invalid reset request.", "error")
            return redirect(url_for('forgot_password'))

        if not user['reset_token'] or user['reset_token'] != reset_token:
            flash("Invalid or incorrect reset code.", "error")
            return render_template('reset_password.html', email=email)

        try:
            expiry_dt = datetime.fromisoformat(str(user['reset_expiry']))
        except Exception:
            expiry_dt = datetime.now() - timedelta(seconds=1)

        if datetime.now() > expiry_dt:
            flash("Reset code has expired. Please request a new one.", "error")
            return redirect(url_for('forgot_password'))

        new_hash = generate_password_hash(new_password)
        update_password(email, new_hash)
        flash("Password reset successfully! You can now log in with your new password.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', email=email)

@app.route('/logout')
def logout():
    """Logs out user, clears session and prevents browser from caching credentials"""
    session.clear()
    flash("You have been signed out successfully.", "info")
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.after_request
def add_security_headers(response):
    """Enforces no-cache policy on sensitive authentication views"""
    if request.endpoint in ['login', 'register', 'verify_email', 'reset_password', 'logout']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ==========================================
# Protected Deepfake Detection Routes
# ==========================================
@app.route('/')
@login_required
def index():
    """Renders the protected Deepfake Detection dashboard"""
    metrics_exists = os.path.exists(os.path.join(PROJECT_DIR, "static", "confusion_matrix.png"))
    return render_template('index.html', has_metrics=metrics_exists, user_name=session.get('user_name'))

@app.route('/predict', methods=['POST'])
@login_required
def api_predict():
    """Protected AJAX API endpoint for instant asynchronous image analysis"""
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image file provided in request."}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": "Invalid format. Allowed formats are: JPG, JPEG, PNG, WEBP."
        }), 400

    try:
        mode = request.form.get('mode', 'standard')
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"upload_{uuid.uuid4().hex[:10]}.{ext}"
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(saved_path)

        engine = get_predictor()
        result = engine.predict(saved_path, mode=mode, save_artifacts=True)
        gc.collect()

        result["success"] = True
        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["uploaded_image_url"] = url_for('static', filename=f"uploads/{unique_name}")
        result["face_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['face_image_path'])}")
        result["annotated_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['annotated_image_path'])}")
        result["ela_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['ela_image_path'])}")
        result["fft_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['fft_image_path'])}")

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
@login_required
def form_analyze():
    """Protected form fallback endpoint"""
    if 'image' not in request.files:
        flash("No image file uploaded.")
        return redirect(url_for('index'))

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        flash("Please upload a valid JPG, JPEG, or PNG image.")
        return redirect(url_for('index'))

    try:
        mode = request.form.get('mode', 'standard')
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"upload_{uuid.uuid4().hex[:10]}.{ext}"
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(saved_path)

        engine = get_predictor()
        result = engine.predict(saved_path, mode=mode, save_artifacts=True)
        gc.collect()

        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["uploaded_image_url"] = url_for('static', filename=f"uploads/{unique_name}")
        result["face_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['face_image_path'])}")
        result["annotated_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['annotated_image_path'])}")
        result["ela_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['ela_image_path'])}")
        result["fft_image_url"] = url_for('static', filename=f"uploads/{os.path.basename(result['fft_image_path'])}")

        return render_template('result.html', result=result)

    except Exception as e:
        flash(f"Error processing image: {str(e)}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
