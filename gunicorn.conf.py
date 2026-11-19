import os

# Render dynamically assigns PORT (defaults to 10000)
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Lean resource allocation for 512MB RAM budget (Single worker + multithreading)
workers = 1
threads = 4
timeout = 120
