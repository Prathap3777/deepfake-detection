"""
Module: database.py
Purpose: SQLite Database Management for User Authentication, OTP Verification & Password Reset
"""
import sqlite3
import os
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "users.db")

def get_db_connection():
    """Returns a SQLite database connection with row dictionary access"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database and creates the users table if not exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            otp_code TEXT,
            otp_expiry TIMESTAMP,
            otp_attempts INTEGER DEFAULT 0,
            reset_token TEXT,
            reset_expiry TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    print("[✓] SQLite database initialized at:", DB_PATH)

def get_user_by_email(email):
    """Retrieves a user record by email"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Retrieves a user record by primary key ID"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def create_user(full_name, email, password_hash, otp_code, otp_expiry):
    """Inserts a new unverified user record with generated OTP"""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO users (full_name, email, password_hash, is_verified, otp_code, otp_expiry, otp_attempts)
            VALUES (?, LOWER(?), ?, 0, ?, ?, 0)
        """, (full_name.strip(), email.strip(), password_hash, otp_code, otp_expiry))
        conn.commit()
        return True, "User registered successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email address already exists."
    finally:
        conn.close()

def update_user_otp(email, otp_code, otp_expiry):
    """Updates OTP code, expiry, and resets attempt counter for resending"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET otp_code = ?, otp_expiry = ?, otp_attempts = 0
        WHERE LOWER(email) = LOWER(?)
    """, (otp_code, otp_expiry, email.strip()))
    conn.commit()
    conn.close()

def increment_otp_attempts(email):
    """Increments failed verification attempts counter"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET otp_attempts = otp_attempts + 1
        WHERE LOWER(email) = LOWER(?)
    """, (email.strip(),))
    conn.commit()
    conn.close()

def activate_user(email):
    """Marks user as email-verified and clears OTP data"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET is_verified = 1, otp_code = NULL, otp_expiry = NULL, otp_attempts = 0
        WHERE LOWER(email) = LOWER(?)
    """, (email.strip(),))
    conn.commit()
    conn.close()

def set_reset_token(email, reset_token, reset_expiry):
    """Stores password reset verification code with expiry"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET reset_token = ?, reset_expiry = ?
        WHERE LOWER(email) = LOWER(?)
    """, (reset_token, reset_expiry, email.strip()))
    conn.commit()
    conn.close()

def update_password(email, new_password_hash):
    """Updates user password and clears reset token"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET password_hash = ?, reset_token = NULL, reset_expiry = NULL
        WHERE LOWER(email) = LOWER(?)
    """, (new_password_hash, email.strip()))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
