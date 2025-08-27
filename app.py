import os
import time
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# -------------------------------
# CONFIG & CLIENTS
# -------------------------------
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Flask app
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Supabase clients
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

# Admin email
ADMIN_EMAIL = "adrimarsh898@gmail.com"

# -------------------------------
# HELPERS
# -------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['email'] != ADMIN_EMAIL:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------
# ROUTES
# -------------------------------

@app.route('/')
def index():
    response = supabase.table('songs').select('*').order('created_at', desc=True).execute()
    songs = response.data if response.data else []
    user = session.get('user')
    return render_template('index.html', songs=songs, user=user)

# -------------------------------
# SIGNUP
# -------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')

        if not all([email, password, username]):
            flash("All fields are required.", "error")
            return redirect(url_for('signup'))

        try:
            auth_response = supabase.auth.sign_up({"email": email, "password": password})
            if not auth_response.user:
                flash("Signup failed. Try again.", "error")
                return redirect(url_for('signup'))

            # Create profile using admin client to bypass RLS
            supabase_admin.table('profiles').insert({
                "id": auth_response.user.id,
                "username": username,
                "email": email
            }).execute()

            session['user'] = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token
            }

            flash("Signup successful!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            print(f"Signup error: {e}")
            flash("Error creating account. Try again.", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')

# -------------------------------
# LOGIN
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password required.", "error")
            return redirect(url_for('login'))

        try:
            auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})

            if not auth_response.user:
                flash("Invalid login credentials.", "error")
                return redirect(url_for('login'))

            session['user'] = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token
            }

            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            print(f"Login error: {e}")
            flash("Invalid credentials or server error.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# -------------------------------
# FORGOT PASSWORD
# -------------------------------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("Please enter your email.", "error")
            return redirect(url_for('forgot_password'))

        try:
            # Use admin client to generate reset link
            reset_response = supabase_admin.auth.admin.generate_link_for_reset_password(email)
            if reset_response.get('data'):
                flash("Password reset instructions sent to your email.", "success")
            else:
                flash("No user found with that email.", "error")
        except Exception as e:
            print(f"Forgot password error: {e}")
            flash("Something went wrong. Try again later.", "error")

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# -------------------------------
# LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# -------------------------------
# UPLOAD (ADMIN ONLY)
# -------------------------------
@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        artist = request.form.get('artist')
        featured_artist = request.form.get('featured_artist', '')
        audio_file = request.files.get('audio_file')
        cover_image = request.files.get('cover_image')

        if not all([title, artist, audio_file, cover_image]):
            return render_template('upload.html', error="All fields except featured artist are required")

        try:
            # Upload audio
            audio_path = f"audios/{int(time.time())}_{audio_file.filename}"
            supabase_admin.storage.from_('music').upload(audio_path, audio_file.read(), {"contentType": audio_file.content_type})
            audio_url = supabase_admin.storage.from_('music').get_public_url(audio_path)

            # Upload cover
            cover_path = f"covers/{int(time.time())}_{cover_image.filename}"
            supabase_admin.storage.from_('covers').upload(cover_path, cover_image.read(), {"contentType": cover_image.content_type})
            cover_url = supabase_admin.storage.from_('covers').get_public_url(cover_path)

            # Insert metadata
            supabase_admin.table('songs').insert({
                "title": title,
                "artist": artist,
                "featured_artist": featured_artist,
                "audio_url": audio_url,
                "cover_url": cover_url,
                "streams": 0,
                "likes": 0
            }).execute()

            flash("Song uploaded successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            print(f"Upload error: {e}")
            return render_template('upload.html', error=str(e))

    return render_template('upload.html')

# -------------------------------
# Other routes (search, like, stream, profile, admin) remain the same
# -------------------------------

# -------------------------------
# ERROR HANDLERS
# -------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# -------------------------------
# RUN APP
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
