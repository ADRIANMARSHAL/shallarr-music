# Phase 1 Migration Guide - Security & Stability Refactor

## 🎯 What Changed

### Critical Security Fixes
1. ✅ **Presigned URLs** - Eliminates RAM loading issue
2. ✅ **Proper Auth Separation** - No more service role for user operations
3. ✅ **Token Refresh** - Automatic session management
4. ✅ **Rate Limiting** - Protection against abuse
5. ✅ **File Validation** - Magic number verification
6. ✅ **Error Handling** - Secure logging, no data leakage
7. ✅ **Session Security** - Mandatory strong SECRET_KEY

## 📋 Step-by-Step Migration

### Step 1: Install Dependencies

```bash
cd /home/collins/Desktop/shallarr-music

# Install new dependencies
pip install flask-limiter flask-talisman python-magic

# Or use updated requirements
pip install -r requirements_updated.txt
```

**Note:** `python-magic` requires libmagic:
- **Ubuntu/Debian:** `sudo apt-get install libmagic1`
- **macOS:** `brew install libmagic`
- **Windows:** Download from: https://github.com/pidydx/libmagicwin64

### Step 2: Update Environment Variables

Add to your `.env` file:

```bash
# CRITICAL: Generate a new secret key
SECRET_KEY=your-generated-secret-key-here

# Supabase credentials (rename SUPABASE_KEY to clarify it's anon key)
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-anon-public-key  # This respects RLS
SUPABASE_SERVICE_KEY=your-service-role-key  # Admin operations only

# Admin email
ADMIN_EMAIL=adrimarsh898@gmail.com

# Optional
FLASK_ENV=development  # Set to 'production' in prod
PORT=5000
```

**Generate a secure SECRET_KEY:**
```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

### Step 3: Set Up Supabase Database

You need to create database functions for atomic operations:

```sql
-- Function to increment stream count
CREATE OR REPLACE FUNCTION increment_streams(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET streams = streams + 1 WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment like count
CREATE OR REPLACE FUNCTION increment_likes(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET likes = likes + 1 WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to decrement like count
CREATE OR REPLACE FUNCTION decrement_likes(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET likes = GREATEST(likes - 1, 0) WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Create likes table if it doesn't exist:**
```sql
CREATE TABLE IF NOT EXISTS likes (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, song_id)
);

-- Row-Level Security
ALTER TABLE likes ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own likes
CREATE POLICY "Users can manage own likes" ON likes
  FOR ALL USING (auth.uid() = user_id);
```

**Ensure profiles table has proper RLS:**
```sql
-- Profiles RLS (if not already set)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can read all profiles
CREATE POLICY "Profiles are viewable by everyone" ON profiles
  FOR SELECT USING (true);

-- Users can update only their own profile
CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);
```

### Step 4: Update Storage Buckets

Ensure your Supabase storage buckets have correct settings:

```sql
-- Make buckets public (for public song URLs)
UPDATE storage.buckets 
SET public = true 
WHERE name IN ('music', 'covers');

-- Set file size limits
UPDATE storage.buckets 
SET file_size_limit = 52428800  -- 50MB
WHERE name = 'music';

UPDATE storage.buckets 
SET file_size_limit = 10485760  -- 10MB
WHERE name = 'covers';

-- Set allowed MIME types
UPDATE storage.buckets 
SET allowed_mime_types = ARRAY['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg']
WHERE name = 'music';

UPDATE storage.buckets 
SET allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp']
WHERE name = 'covers';
```

### Step 5: Test the Refactored App

**Backup your current app.py:**
```bash
cp app.py app_old.py
```

**Replace with refactored version:**
```bash
cp app_refactored.py app.py
```

**Run the app:**
```bash
python app.py
```

**Test checklist:**
- [ ] Can sign up new user
- [ ] Can log in
- [ ] Session persists (doesn't log out after 1 hour)
- [ ] Admin can access /upload page
- [ ] Rate limiting works (try 6 signups - should block)
- [ ] Songs display on homepage
- [ ] Can like/unlike songs (if logged in)
- [ ] Search works

## 🔄 Frontend Changes Required

The upload form needs to be updated to use presigned URLs. Here's the new flow:

### Current Upload Form (upload.html)
```html
<!-- OLD: Uploads through Flask server -->
<form method="POST" enctype="multipart/form-data">
    <input type="file" name="audio_file">
    <input type="file" name="cover_image">
    <button type="submit">Upload</button>
</form>
```

### New Upload Form (requires JavaScript)
```html
<form id="upload-form">
    <input type="text" id="title" required>
    <input type="text" id="artist" required>
    <input type="text" id="featured_artist">
    <input type="file" id="audio_file" accept="audio/*" required>
    <input type="file" id="cover_image" accept="image/*" required>
    
    <div id="upload-progress" style="display: none;">
        <div class="progress-bar">
            <div id="progress-fill" style="width: 0%"></div>
        </div>
        <p id="progress-text">Preparing upload...</p>
    </div>
    
    <button type="submit" id="upload-btn">Upload Song</button>
</form>

<script>
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = document.getElementById('title').value;
    const artist = document.getElementById('artist').value;
    const featured_artist = document.getElementById('featured_artist').value;
    const audioFile = document.getElementById('audio_file').files[0];
    const coverFile = document.getElementById('cover_image').files[0];
    
    const uploadBtn = document.getElementById('upload-btn');
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    // Disable button
    uploadBtn.disabled = true;
    progressDiv.style.display = 'block';
    
    try {
        // Step 1: Request presigned URLs
        progressText.textContent = 'Requesting upload URLs...';
        
        const urlResponse = await fetch('/api/request-upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                audio_filename: audioFile.name,
                cover_filename: coverFile.name,
                audio_size: audioFile.size,
                cover_size: coverFile.size
            })
        });
        
        if (!urlResponse.ok) {
            const error = await urlResponse.json();
            throw new Error(error.error || 'Could not get upload URLs');
        }
        
        const uploadData = await urlResponse.json();
        
        // Step 2: Upload audio file
        progressText.textContent = 'Uploading audio file...';
        
        const audioFormData = new FormData();
        audioFormData.append('file', audioFile);
        
        const audioUploadResponse = await fetch(uploadData.audio_upload_url, {
            method: 'PUT',
            body: audioFile,
            headers: {
                'Content-Type': audioFile.type
            }
        });
        
        if (!audioUploadResponse.ok) {
            throw new Error('Audio upload failed');
        }
        
        progressFill.style.width = '50%';
        
        // Step 3: Upload cover image
        progressText.textContent = 'Uploading cover image...';
        
        const coverUploadResponse = await fetch(uploadData.cover_upload_url, {
            method: 'PUT',
            body: coverFile,
            headers: {
                'Content-Type': coverFile.type
            }
        });
        
        if (!coverUploadResponse.ok) {
            throw new Error('Cover upload failed');
        }
        
        progressFill.style.width = '75%';
        
        // Step 4: Finalize upload (save metadata)
        progressText.textContent = 'Saving song details...';
        
        const finalizeResponse = await fetch('/api/finalize-upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                artist: artist,
                featured_artist: featured_artist,
                audio_path: uploadData.audio_path,
                cover_path: uploadData.cover_path,
                upload_id: uploadData.upload_id
            })
        });
        
        if (!finalizeResponse.ok) {
            const error = await finalizeResponse.json();
            throw new Error(error.error || 'Could not save song metadata');
        }
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete!';
        
        // Redirect to home after 1 second
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
        
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed: ' + error.message);
        uploadBtn.disabled = false;
        progressDiv.style.display = 'none';
    }
});
</script>
```

## 🚨 Breaking Changes

### 1. Environment Variables
- `SECRET_KEY` is now **required** (app won't start without it)
- If you used "dev-key-change", app will crash - this is intentional for security

### 2. Signup Flow
- Old: Used `supabase_admin` to create profile
- New: Relies on Supabase database trigger or user metadata
- **Action Required:** Set up profile creation trigger in Supabase:

```sql
-- Trigger to auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username, email, created_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
    NEW.email,
    NOW()
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 3. Upload Flow
- Old: Synchronous form POST with file upload
- New: Asynchronous JavaScript with presigned URLs
- **Action Required:** Update upload.html with JavaScript code above

### 4. Session Management
- Sessions now include `refresh_token` and `expires_at`
- Old sessions will be invalid (users need to re-login once)

## 🧪 Testing Checklist

### Authentication Tests
```bash
# Test 1: Signup rate limiting
# Try to sign up 6 times in an hour - 6th should fail with 429

# Test 2: Token refresh
# Log in, wait 55 minutes (or mock it), make a request
# Token should auto-refresh

# Test 3: Session security
# Ensure SECRET_KEY is strong
# Try to decode session cookie - should be secure
```

### Upload Tests
```bash
# Test 1: Size validation
# Try uploading 100MB audio file - should reject

# Test 2: Type validation
# Try uploading .exe file as audio - should reject

# Test 3: Orphaned file cleanup
flask cleanup-orphaned-files
# Should detect and remove orphaned files
```

### Security Tests
```bash
# Test 1: RLS enforcement
# Create non-admin user
# Try to access /admin - should redirect
# Try to access /upload - should redirect

# Test 2: CSRF protection
# Try making POST request without proper headers
# Should fail (once CSRF middleware is fully enabled)
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
```bash
pip install -r requirements_updated.txt
```

### "ModuleNotFoundError: No module named 'magic'"
Install libmagic system library first, then:
```bash
pip install python-magic
```

### "RuntimeError: SECRET_KEY must be set"
Generate and set in `.env`:
```bash
python -c 'import secrets; print(secrets.token_hex(32))'
# Copy output to .env file
```

### "create_signed_upload_url() not found"
Update supabase-py library:
```bash
pip install --upgrade supabase storage3
```

### "Users logged out immediately"
Check if profile creation trigger exists:
```sql
SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
```

### "Upload fails at finalization"
Check if files exist in storage:
```sql
SELECT * FROM storage.objects WHERE bucket_id IN ('music', 'covers');
```

## 📊 Performance Improvements

### Before Refactor
- **Upload**: 50MB file loads into RAM → 50MB memory used
- **10 concurrent uploads**: 500MB RAM → Server crash
- **Session lifetime**: 1 hour → Users logged out
- **Error messages**: Raw exceptions exposed

### After Refactor
- **Upload**: Direct to Supabase → 0MB memory used
- **10 concurrent uploads**: 0MB RAM on server
- **Session lifetime**: Auto-refresh → Users stay logged in
- **Error messages**: Generic messages → No data leakage

## 🎉 Next Steps

Once Phase 1 is stable:
1. **Phase 2**: Add HTMX for seamless navigation
2. **Phase 2**: Add Alpine.js for interactivity
3. **Phase 2**: Build local Tailwind CSS
4. **Phase 3**: Performance optimization & monitoring

## 📞 Support

If you encounter issues:
1. Check logs: `tail -f app.log`
2. Check Supabase dashboard for errors
3. Verify environment variables are set
4. Test with original app.py to isolate issue

---

**Migration Status:** Ready for Testing  
**Last Updated:** February 5, 2026  
**Next Review:** After Phase 1 testing complete
