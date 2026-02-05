import os
import time
import uuid
import logging
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from dotenv import load_dotenv
from supabase import create_client
import magic

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================================================================================
# CONFIG
# ================================================================================================

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY or SECRET_KEY == 'dev-key-change':
        raise RuntimeError("SECRET_KEY must be set! Generate: python -c 'import secrets; print(secrets.token_hex(32))'")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if not all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY]):
        raise RuntimeError("Supabase credentials required")
    
    MAX_AUDIO_SIZE = 50 * 1024 * 1024
    MAX_COVER_SIZE = 10 * 1024 * 1024
    ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg']
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
    TOKEN_REFRESH_BUFFER = 300

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'adrimarsh898@gmail.com')

# ================================================================================================
# AUTHENTICATION HELPERS
# ================================================================================================

def get_authenticated_client():
    if 'user' not in session:
        return None
    
    access_token = session['user'].get('access_token')
    if not access_token:
        return None
    
    auth_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
    auth_client.postgrest.auth(access_token)
    return auth_client

def check_token_expiry():
    if 'user' not in session:
        return False
    
    expires_at = session['user'].get('expires_at', 0)
    current_time = time.time()
    
    return (expires_at - current_time) < Config.TOKEN_REFRESH_BUFFER

def refresh_user_token():
    if 'user' not in session:
        return False
    
    refresh_token = session['user'].get('refresh_token')
    if not refresh_token:
        logger.warning("No refresh token found")
        return False
    
    try:
        response = supabase.auth.refresh_session(refresh_token)
        
        if response.session:
            session['user']['access_token'] = response.session.access_token
            session['user']['refresh_token'] = response.session.refresh_token
            session['user']['expires_at'] = response.session.expires_at
            logger.info(f"Token refreshed for user {session['user']['id']}")
            return True
        else:
            logger.warning("Token refresh failed")
            return False
            
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return False

@app.before_request
def refresh_token_if_needed():
    if 'user' in session and check_token_expiry():
        if not refresh_user_token():
            session.pop('user', None)
            if request.endpoint not in ['login', 'signup', 'index', 'static']:
                flash("Session expired. Please log in again.", "warning")
                return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        
        if session['user'].get('email') != ADMIN_EMAIL:
            flash("Permission denied.", "error")
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# ================================================================================================
# FILE VALIDATION
# ================================================================================================

def validate_file_type(file_obj, allowed_types, file_category="file"):
    try:
        header = file_obj.read(2048)
        file_obj.seek(0)
        
        mime = magic.from_buffer(header, mime=True)
        
        if mime not in allowed_types:
            return False, mime, f"Invalid {file_category} type: {mime}"
        
        return True, mime, None
        
    except Exception as e:
        logger.error(f"File validation error: {e}")
        return False, None, f"Could not validate {file_category}"

def validate_file_size(file_obj, max_size, file_category="file"):
    try:
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        
        if size > max_size:
            size_mb = size / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            return False, f"{file_category} too large: {size_mb:.1f}MB. Max: {max_mb:.0f}MB"
        
        return True, None
        
    except Exception as e:
        logger.error(f"File size validation error: {e}")
        return False, f"Could not validate {file_category} size"


# ================================================================================================
# ROUTES
# ================================================================================================

@app.route('/')
def index():
    try:
        response = supabase.table('songs').select('*').order('created_at', desc=True).limit(50).execute()
        songs = response.data if response.data else []
        
        # Get user's liked songs if logged in
        user_likes = set()
        user = session.get('user')
        if user:
            try:
                auth_client = get_authenticated_client()
                if auth_client:
                    likes_response = auth_client.table('likes').select('song_id').eq('user_id', user['id']).execute()
                    user_likes = {like['song_id'] for like in likes_response.data}
            except Exception as e:
                logger.error(f"Error fetching user likes: {e}")
        
        # Add liked status to each song
        for song in songs:
            song['is_liked'] = song['id'] in user_likes
            
    except Exception as e:
        logger.error(f"Error fetching songs: {e}")
        songs = []
        flash("Could not load songs.", "error")
    
    return render_template('index.html', songs=songs, user=user, ADMIN_EMAIL=ADMIN_EMAIL)

# ================================================================================================
# AUTHENTICATION
# ================================================================================================

@app.route('/signup', methods=['GET', 'POST'])
# @limiter.limit("5 per hour")  # Temporarily disabled for testing
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        username = request.form.get('username', '').strip()

        if not all([email, password, username]):
            flash("All fields required.", "error")
            return redirect(url_for('signup'))
        
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for('signup'))
        
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return redirect(url_for('signup'))

        try:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"username": username}}
            })
            
            if not auth_response.user:
                flash("Signup failed. Email may be in use.", "error")
                return redirect(url_for('signup'))
            
            if not auth_response.session:
                flash("Account created! Check your email to confirm your account.", "success")
                return redirect(url_for('login'))
            
            session['user'] = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "username": username,
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_at": auth_response.session.expires_at
            }

            flash("Account created successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Signup error: {e}", exc_info=True)
            flash("Could not create account.", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("30 per hour")
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash("Email and password required.", "error")
            return redirect(url_for('login'))

        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user or not auth_response.session:
                flash("Invalid credentials.", "error")
                return redirect(url_for('login'))
            
            username = auth_response.user.user_metadata.get('username', email.split('@')[0])

            session['user'] = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "username": username,
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_at": auth_response.session.expires_at
            }

            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            flash("Invalid credentials.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        if 'user' in session:
            supabase.auth.sign_out()
    except Exception as e:
        logger.error(f"Logout error: {e}")
    
    session.pop('user', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Please enter your email.", "error")
            return redirect(url_for('forgot_password'))

        try:
            supabase.auth.reset_password_email(email)
            flash("If account exists, you will receive reset instructions.", "info")
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            flash("If account exists, you will receive reset instructions.", "info")

        return redirect(url_for('login'))

    return render_template('forgot_password.html')

# ================================================================================================
# UPLOAD (PRESIGNED URLS)
# ================================================================================================

@app.route('/upload', methods=['GET'])
@admin_required
def upload_page():
    return render_template('upload.html')

@app.route('/api/request-upload', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")
def request_upload():
    try:
        data = request.get_json()
        
        audio_filename = data.get('audio_filename')
        cover_filename = data.get('cover_filename')
        audio_size = data.get('audio_size', 0)
        cover_size = data.get('cover_size', 0)
        
        if not all([audio_filename, cover_filename]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if audio_size > Config.MAX_AUDIO_SIZE:
            return jsonify({'error': f'Audio too large. Max: {Config.MAX_AUDIO_SIZE / (1024*1024):.0f}MB'}), 400
        
        if cover_size > Config.MAX_COVER_SIZE:
            return jsonify({'error': f'Cover too large. Max: {Config.MAX_COVER_SIZE / (1024*1024):.0f}MB'}), 400
        
        def sanitize_filename(filename):
            name, ext = os.path.splitext(filename)
            name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            return f"{name}{ext}"
        
        upload_id = str(uuid.uuid4())
        safe_audio_name = sanitize_filename(audio_filename)
        safe_cover_name = sanitize_filename(cover_filename)
        audio_path = f"audios/{upload_id}_{safe_audio_name}"
        cover_path = f"{upload_id}_{safe_cover_name}"
        
        audio_upload_data = supabase_admin.storage.from_('music').create_signed_upload_url(audio_path)
        cover_upload_data = supabase_admin.storage.from_('covers').create_signed_upload_url(cover_path)
        
        return jsonify({
            'upload_id': upload_id,
            'audio_upload_url': audio_upload_data['signedUrl'],
            'audio_path': audio_path,
            'audio_token': audio_upload_data['token'],
            'cover_upload_url': cover_upload_data['signedUrl'],
            'cover_path': cover_path,
            'cover_token': cover_upload_data['token'],
            'expires_in': 900
        }), 200
        
    except Exception as e:
        logger.error(f"Upload URL generation error: {e}", exc_info=True)
        return jsonify({'error': 'Could not generate upload URLs'}), 500

@app.route('/api/finalize-upload', methods=['POST'])
@admin_required
def finalize_upload():
    try:
        data = request.get_json()
        
        title = data.get('title', '').strip()
        artist = data.get('artist', '').strip()
        featured_artist = (data.get('featured_artist') or '').strip()
        audio_path = data.get('audio_path')
        cover_path = data.get('cover_path')
        upload_id = data.get('upload_id')
        
        if not all([title, artist, audio_path, cover_path, upload_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            audio_info = supabase_admin.storage.from_('music').list(path=os.path.dirname(audio_path))
            cover_info = supabase_admin.storage.from_('covers').list(path=os.path.dirname(cover_path))
            
            audio_exists = any(f['name'] == os.path.basename(audio_path) for f in audio_info)
            cover_exists = any(f['name'] == os.path.basename(cover_path) for f in cover_info)
            
            if not audio_exists or not cover_exists:
                return jsonify({'error': 'File verification failed'}), 400
                
        except Exception as e:
            logger.error(f"File verification error: {e}")
            return jsonify({'error': 'Could not verify files'}), 500
        
        audio_url = supabase_admin.storage.from_('music').get_public_url(audio_path)
        cover_url = supabase_admin.storage.from_('covers').get_public_url(cover_path)
        
        song_data = {
            "title": title,
            "artist": artist,
            "featured_artist": featured_artist if featured_artist else None,
            "audio_url": audio_url,
            "cover_url": cover_url,
            "uploader_id": session['user']['id'],
            "streams": 0,
            "likes": 0,
            "created_at": datetime.now(datetime.UTC).isoformat()
        }
        
        result = supabase_admin.table('songs').insert(song_data).execute()
        
        if result.data:
            logger.info(f"Song uploaded: {title} by {artist}")
            return jsonify({
                'success': True,
                'song_id': result.data[0]['id'],
                'message': 'Song uploaded successfully!'
            }), 200
        else:
            return jsonify({'error': 'Could not save song metadata'}), 500
        
    except Exception as e:
        logger.error(f"Upload finalization error: {e}", exc_info=True)
        return jsonify({'error': 'Could not finalize upload'}), 500

# ================================================================================================
# MUSIC INTERACTION
# ================================================================================================

@app.route('/stream/<int:song_id>', methods=['POST'])
def stream_song(song_id):
    try:
        supabase.rpc('increment_streams', {'song_id': song_id}).execute()
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Stream increment error: {e}")
        return jsonify({'error': 'Could not update stream count'}), 500

@app.route('/like/<int:song_id>', methods=['POST'])
@login_required
def like_song(song_id):
    try:
        user_id = session['user']['id']
        auth_client = get_authenticated_client()
        
        if not auth_client:
            return jsonify({'error': 'Authentication required'}), 401
        
        existing = auth_client.table('likes').select('*').eq('user_id', user_id).eq('song_id', song_id).execute()
        
        if existing.data:
            # Unlike
            auth_client.table('likes').delete().eq('user_id', user_id).eq('song_id', song_id).execute()
            auth_client.rpc('decrement_likes', {'song_id': song_id}).execute()
            is_liked = False
        else:
            # Like
            auth_client.table('likes').insert({'user_id': user_id, 'song_id': song_id}).execute()
            auth_client.rpc('increment_likes', {'song_id': song_id}).execute()
            is_liked = True
        
        # Get updated like count
        song = auth_client.table('songs').select('likes').eq('id', song_id).single().execute()
        like_count = song.data['likes'] if song.data else 0
        
        # Return HTML for HTMX swap
        icon_class = 'fas' if is_liked else 'far'
        text_class = 'text-purple-600 dark:text-purple-400' if is_liked else 'text-gray-500 dark:text-gray-400'
        
        html = f'''
        <button hx-post="/like/{song_id}" 
                hx-swap="outerHTML" 
                hx-target="this"
                class="like-btn flex items-center {text_class} hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
            <i class="{icon_class} fa-heart mr-1"></i>
            <span class="like-count">{like_count}</span>
        </button>
        '''
        return html, 200
            
    except Exception as e:
        logger.error(f"Like toggle error: {e}")
        return '<span class="text-red-500 text-xs">Error</span>', 500

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('search.html', songs=[], query='')
    
    try:
        response = supabase.table('songs').select('*').or_(
            f"title.ilike.%{query}%,artist.ilike.%{query}%,featured_artist.ilike.%{query}%"
        ).limit(50).execute()
        
        songs = response.data if response.data else []
        
        # Get user's liked songs if logged in
        user_likes = set()
        user = session.get('user')
        if user:
            try:
                auth_client = get_authenticated_client()
                if auth_client:
                    likes_response = auth_client.table('likes').select('song_id').eq('user_id', user['id']).execute()
                    user_likes = {like['song_id'] for like in likes_response.data}
            except Exception as e:
                logger.error(f"Error fetching user likes: {e}")
        
        # Add liked status to each song
        for song in songs:
            song['is_liked'] = song['id'] in user_likes
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        songs = []
        flash("Search failed.", "error")
    
    return render_template('search.html', songs=songs, query=query)

@app.route('/profile')
@login_required
def profile():
    try:
        user_id = session['user']['id']
        auth_client = get_authenticated_client()
        
        profile_data = auth_client.table('profiles').select('*').eq('id', user_id).execute()
        profile = profile_data.data[0] if profile_data.data else None
        
        if not profile:
            flash("Profile not found.", "error")
            return redirect(url_for('index'))
        
        likes = auth_client.table('likes').select('song_id').eq('user_id', user_id).execute()
        liked_song_ids = [like['song_id'] for like in likes.data] if likes.data else []
        
        if liked_song_ids:
            liked_songs = supabase.table('songs').select('*').in_('id', liked_song_ids).execute()
            songs = liked_songs.data if liked_songs.data else []
        else:
            songs = []
        
    except Exception as e:
        logger.error(f"Profile page error: {e}")
        songs = []
        profile = None
        flash("Could not load profile.", "error")
    
    return render_template('profile.html', songs=songs, user=session['user'], profile=profile)

@app.route('/admin')
@admin_required
def admin_page():
    try:
        songs = supabase_admin.table('songs').select('*').order('created_at', desc=True).execute()
        
        users = supabase_admin.table('profiles').select('id', count='exact').execute()
        user_count = users.count if users.count else 0
        
        total_streams = sum(song.get('streams', 0) for song in songs.data) if songs.data else 0
        
        stats = {
            'total_songs': len(songs.data) if songs.data else 0,
            'total_users': user_count,
            'total_streams': total_streams
        }
        
    except Exception as e:
        logger.error(f"Admin page error: {e}")
        songs = []
        stats = {'total_songs': 0, 'total_users': 0, 'total_streams': 0}
        flash("Could not load admin data.", "error")
    
    return render_template('admin.html', songs=songs.data if songs.data else [], stats=stats)

# ================================================================================================
# ERROR HANDLERS
# ================================================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_error(error):
    return jsonify({'error': 'Too many requests'}), 429

# ================================================================================================
# CLI COMMANDS
# ================================================================================================

@app.cli.command()
def cleanup_orphaned_files():
    logger.info("Starting orphaned file cleanup...")
    
    try:
        storage_files = supabase_admin.storage.from_('music').list()
        
        db_songs = supabase_admin.table('songs').select('audio_url').execute()
        db_paths = set()
        
        for song in db_songs.data:
            url = song['audio_url']
            path = url.split('/music/')[-1] if '/music/' in url else None
            if path:
                db_paths.add(path)
        
        deleted_count = 0
        for file in storage_files:
            if file['name'] not in db_paths:
                created = datetime.fromisoformat(file['created_at'].replace('Z', '+00:00'))
                age = datetime.now(created.tzinfo) - created
                
                if age > timedelta(days=1):
                    supabase_admin.storage.from_('music').remove([file['name']])
                    logger.info(f"Deleted orphaned file: {file['name']}")
                    deleted_count += 1
        
        logger.info(f"Cleanup complete. Deleted {deleted_count} files.")
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}", exc_info=True)

# ================================================================================================
# RUN APP
# ================================================================================================

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    if not debug:
        logger.warning("Running in production mode")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
