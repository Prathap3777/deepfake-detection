# Deepfake Image Detection and Face Authenticity Check

An end-to-end AI-powered web application that detects whether an uploaded human face image is **REAL** or **FAKE / AI-GENERATED** using Deep Learning (PyTorch ResNet-18 Transfer Learning), Multi-Domain Digital Forensics (Laplacian Sensor Noise, 2D-FFT Spectral Analysis), and a secure Instagram-style Authentication System.

---

## 🌟 Key Features
- **Instagram-Style Authentication:**
  - Modern, minimalist login and registration interface.
  - Smart automatic email suggestion (populates `@gmail.com`, `@outlook.com`, etc. as you type).
  - Dynamic **"Show / Hide"** password toggle.
  - Automatic password clearing upon sign out (anti-autofill protection).
- **Email Verification via 6-Digit OTP:**
  - Generates a secure random 6-digit OTP code sent via SMTP (Gmail App Password).
  - Enforces a 5-minute expiration timer and a 5-attempt rate limit.
  - Resend OTP functionality.
- **Forgot & Reset Password Recovery:**
  - Users can request a 6-digit password reset code sent to their registered email.
  - Securely updates the password in SQLite using Werkzeug salted hashing.
- **Session Authentication & Route Protection:**
  - Protected Deepfake Detection dashboard accessible only to authenticated, verified users.
  - Secure session logout with strict no-cache HTTP headers.
- **Forensic Face Authenticity Engine:**
  - **Pretrained ResNet-18 Backbone:** Evaluates deep anatomical representations and lighting gradients.
  - **Optical Sensor Noise & Skin Pore Analysis (Laplacian Variance):** Identifies natural camera sensor grain vs. synthetic plastic smoothing.
  - **2D-FFT Frequency Spectrum Analysis:** Flags periodic checkerboard upsampling artifacts left by GANs and diffusion decoders.
  - **Chromatic Channel Coherence:** Inspects RGB sensor well alignment across face contours.
  - **Smart Face Localization:** Isolates the primary human face while filtering out background false positives (pillars, architectural carvings).

---

## 📁 Project Structure
```
deepfake_detection/
├── dataset/
│   ├── real/             # Authentic face portraits
│   ├── fake/             # Manipulated / AI-generated face images
│   └── processed/        # 128x128 face crops (train, val, test)
├── model/
│   ├── haarcascade_frontalface_default.xml  # Face detector cascade
│   ├── deepfake_detector.pt                 # Trained ResNet-18 model weights
│   └── classes.json                         # Class labels (['fake', 'real'])
├── static/
│   ├── css/
│   │   ├── auth.css      # Instagram-style authentication CSS
│   │   └── style.css     # Dark/blue forensic dashboard CSS
│   ├── js/
│   │   └── main.js       # Client-side AJAX & drag-and-drop controller
│   ├── uploads/          # Image processing and crop cache
│   └── confusion_matrix.png # Model evaluation chart
├── templates/
│   ├── login.html        # Instagram-style Login view
│   ├── register.html     # Registration view with smart autocomplete
│   ├── verify_email.html # 6-digit OTP email verification view
│   ├── forgot_password.html # Password reset request view
│   ├── reset_password.html  # Password update view
│   ├── index.html        # Protected Face Authenticity Dashboard
│   └── result.html       # Full-page forensic report
├── app.py                # Flask application backend
├── database.py           # SQLite user database manager
├── mailer.py             # SMTP email dispatcher
├── predict.py            # Hybrid inference & forensic engine
├── train_model.py        # ResNet-18 training script
├── prepare_dataset.py    # Dataset loader & face cropping pipeline
├── test_face_detection.py# Environment verification script
├── Procfile              # Production WSGI process file
├── render.yaml           # 1-Click Render cloud deployment blueprint
├── requirements.txt      # Project dependencies
├── .env.example          # Environment variables template
└── README.md             # Complete documentation
```

---

## 💻 Local Setup & Execution

### 1. Activate Virtual Environment
```powershell
cd C:\Users\prath\OneDrive\Desktop\deepfake_detection
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 2. Configure Email Credentials (Optional for Local Testing)
Open `.env` and set your Gmail App Password:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_16_character_app_password
MAIL_SENDER_NAME="Deepfake Face Authenticity AI"
FLASK_SECRET_KEY=deepfake-auth-secret-key-2026-production
```

### 3. Run the Application
```powershell
python app.py
```
Open your browser and visit:
👉 **`http://127.0.0.1:5000`**

---

## ☁️ Deployment Guide (Render)

### Step A: Push Code to GitHub
1. Initialize git in your project:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit - Complete Deepfake Detection & Auth Web App"
   ```
2. Create a new repository on [GitHub](https://github.com/new) named `deepfake-detection`.
3. Push your code:
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/deepfake-detection.git
   git branch -M main
   git push -u origin main
   ```

### Step B: Deploy on Render (Free Tier)
1. Sign up / Log in to [Render](https://render.com).
2. Click **New +** &rarr; **Web Service**.
3. Connect your GitHub repository `deepfake-detection`.
4. Configure service settings:
   - **Name:** `deepfake-detection-ai`
   - **Region:** Closest to your users (e.g. Frankfurt / Singapore / Oregon)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 2 --timeout 120`
   - **Instance Type:** `Free`
5. Under **Environment Variables**, add:
   - `FLASK_SECRET_KEY` = (any long random secret string)
   - `MAIL_SERVER` = `smtp.gmail.com`
   - `MAIL_PORT` = `587`
   - `MAIL_USE_TLS` = `true`
   - `MAIL_USERNAME` = `your_gmail@gmail.com`
   - `MAIL_PASSWORD` = `your_16_letter_gmail_app_password`
6. Click **Create Web Service**. Render will automatically build the container and deploy your application online!
