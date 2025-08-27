import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from config import Config
from supabase import create_client, Client
import time
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config.from_object(Config)

# Supabase clients
supabase = Config.supabase()
supabase_admin = Config.supabase_admin()

# Admin email
ADMIN_EMAIL = "adrimarsh898@gmail.com"

# Helper function for safe data access
def safe_get_first_item(query_result, default=None):
    """Safely get the first item from a query result"""
    return query_result.data[0] if query_result.data and len(query_result.data) > 0 else default

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('email') != ADMIN_EMAIL:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    # Fetch songs from Supabase, sorted by newest first with error handling
    response = supabase.table('songs').select('*').order('created_at', desc=True).execute()
    songs = response.data if response.data else []
    
    # Get user session if exists
    user = session.get('user', None)
    
    return render_template('index.html', songs=songs, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Sign in with Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Store user in session
            session['user'] = {
                'id': auth_response.user.id,
                'email': auth_response.user.email,
                'access_token': auth_response.session.access_token
            }
            
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('login.html', error=str(e))
    
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("Please enter your email.", "error")
            return redirect(url_for('forgot_password'))

        try:
            # Trigger Supabase password reset email
            supabase_admin.auth.admin.reset_user_password(email=email)
            flash("Password reset instructions sent to your email.", "success")

        except Exception as e:             
            import traceback             
            traceback.print_exc()             
            flash(f"Error: {str(e)}", "error")


        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


            
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        
        try:
            # Sign up with Supabase
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            # Use admin client to bypass RLS for profile creation
            supabase_admin.table('profiles').insert({
                'id': auth_response.user.id,
                'username': username,
                'email': email
            }).execute()
            
            # Store user in session
            session['user'] = {
                'id': auth_response.user.id,
                'email': auth_response.user.email,
                'access_token': auth_response.session.access_token
            }
            
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('signup.html', error=str(e))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    # Clear session
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        artist = request.form.get('artist')
        featured_artist = request.form.get('featured_artist', '')
        audio_file = request.files.get('audio_file')
        cover_image = request.files.get('cover_image')
        
        # Validate required fields
        if not all([title, artist, audio_file, cover_image]):
            return render_template('upload.html', error="All fields except featured artist are required")
        
        try:
            # Use admin client for upload to bypass RLS
            # Upload audio file to Supabase Storage
            audio_path = f"audios/{int(time.time())}_{audio_file.filename}"
            supabase_admin.storage.from_('music').upload(audio_path, audio_file.read(), {
                "contentType": audio_file.content_type
            })
            
            # Upload cover image to Supabase Storage
            cover_path = f"covers/{int(time.time())}_{cover_image.filename}"
            supabase_admin.storage.from_('covers').upload(cover_path, cover_image.read(), {
                "contentType": cover_image.content_type
            })
            
            # Get public URLs
            audio_url = supabase_admin.storage.from_('music').get_public_url(audio_path)
            cover_url = supabase_admin.storage.from_('covers').get_public_url(cover_path)
            
            # Insert song metadata into database using admin client
            supabase_admin.table('songs').insert({
                'title': title,
                'artist': artist,
                'featured_artist': featured_artist,
                'audio_url': audio_url,
                'cover_url': cover_url,
                'streams': 0,
                'likes': 0
            }).execute()
            
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('upload.html', error=str(e))
    
    return render_template('upload.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    songs = []
    error = None
    
    if query:
        try:
            # Method 1: Try individual searches
            title_response = supabase.table('songs')\
                .select('*')\
                .ilike('title', f'%{query}%')\
                .execute()
            
            artist_response = supabase.table('songs')\
                .select('*')\
                .ilike('artist', f'%{query}%')\
                .execute()
            
            # Combine results
            title_songs = title_response.data if title_response.data else []
            artist_songs = artist_response.data if artist_response.data else []
            
            # Remove duplicates
            seen_ids = set()
            songs = []
            
            for song in title_songs + artist_songs:
                if song['id'] not in seen_ids:
                    seen_ids.add(song['id'])
                    songs.append(song)
                    
        except Exception as e:
            error = f"Search error: {str(e)}"
            print(error)
    
    return render_template('search.html', songs=songs, query=query, error=error)

@app.route('/like/<song_id>', methods=['POST'])
@login_required
def like_song(song_id):
    user_id = session['user']['id']
    print(f"Like request: user={user_id}, song={song_id}")
    
    try:
        # Check if song exists first
        song_check = supabase.table('songs').select('id, likes').eq('id', song_id).execute()
        print(f"Song check: {song_check.data}")
        
        if not song_check.data:
            return jsonify({'success': False, 'error': 'Song not found'})
        
        # Check if user already liked the song using admin client
        existing_like = supabase_admin.table('likes').select('*').eq('user_id', user_id).eq('song_id', song_id).execute()
        print(f"Existing like check: {existing_like.data}")
        
        current_likes = song_check.data[0]['likes']
        print(f"Current likes: {current_likes}")
        
        if existing_like.data:
            # Unlike the song
            delete_result = supabase_admin.table('likes').delete().eq('user_id', user_id).eq('song_id', song_id).execute()
            print(f"Delete result: {delete_result}")
            new_likes = max(0, current_likes - 1)
            liked = False
        else:
            # Like the song
            insert_result = supabase_admin.table('likes').insert({
                'user_id': user_id,
                'song_id': song_id
            }).execute()
            print(f"Insert result: {insert_result}")
            new_likes = current_likes + 1
            liked = True
        
        # Update the like count in songs table
        update_result = supabase_admin.table('songs').update({'likes': new_likes}).eq('id', song_id).execute()
        print(f"Update result: {update_result}")
        
        return jsonify({'success': True, 'likes': new_likes, 'liked': liked})
    except Exception as e:
        print(f"Error in like_song: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Unable to process like. Please try again.'})
            
@app.route('/stream/<song_id>', methods=['POST'])
def stream_song(song_id):
    try:
        # Check if song exists first
        song_check = supabase.table('songs').select('streams').eq('id', song_id).execute()
        if not song_check.data:
            return jsonify({'success': False, 'error': 'Song not found'})
        
        # Get current streams safely
        current_streams = song_check.data[0]['streams'] if song_check.data else 0
        
        # Increment stream count
        supabase.table('songs').update({'streams': current_streams + 1}).eq('id', song_id).execute()
        
        # Return success with CORS headers if needed
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    
@app.route('/profile')
@login_required
def profile():
    user_id = session['user']['id']
    
    # Get user profile with error handling
    response = supabase.table('profiles').select('*').eq('id', user_id).execute()
    if not response.data:
        # Use admin client to create profile if it doesn't exist (bypass RLS)
        supabase_admin.table('profiles').insert({
            'id': user_id,
            'username': session['user'].get('email', 'user').split('@')[0],
            'email': session['user'].get('email', '')
        }).execute()
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
    
    profile = response.data[0] if response.data else None
    
    # Get user's liked songs with error handling
    liked_response = supabase.table('likes').select('song_id').eq('user_id', user_id).execute()
    song_ids = [like['song_id'] for like in liked_response.data] if liked_response.data else []
    
    songs = []
    if song_ids:
        songs_response = supabase.table('songs').select('*').in_('id', song_ids).execute()
        songs = songs_response.data if songs_response.data else []
    
    return render_template('profile.html', profile=profile, liked_songs=songs)

@app.route('/admin')
@admin_required
def admin():
    # Get statistics with error handling
    users_response = supabase.table('profiles').select('id').execute()
    users_count = len(users_response.data) if users_response.data else 0
    
    songs_response = supabase.table('songs').select('id').execute()
    songs_count = len(songs_response.data) if songs_response.data else 0
    
    streams_response = supabase.table('songs').select('streams').execute()
    total_streams = sum(song['streams'] for song in streams_response.data) if streams_response.data else 0
    
    likes_response = supabase.table('songs').select('likes').execute()
    total_likes = sum(song['likes'] for song in likes_response.data) if likes_response.data else 0
    
    # Get all songs with details
    songs_response = supabase.table('songs').select('*').order('created_at', desc=True).execute()
    songs = songs_response.data if songs_response.data else []
    
    return render_template('admin.html', 
                         users_count=users_count, 
                         songs_count=songs_count,
                         total_streams=total_streams,
                         total_likes=total_likes,
                         songs=songs)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Use environment variable for port or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)