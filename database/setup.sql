-- Shallarr Music Database Setup
-- Run this in Supabase SQL Editor

-- Tables
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS songs (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  artist TEXT NOT NULL,
  featured_artist TEXT,
  audio_url TEXT NOT NULL,
  cover_url TEXT NOT NULL,
  uploader_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  streams INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS likes (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, song_id)
);

CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id);
CREATE INDEX IF NOT EXISTS idx_likes_song_id ON likes(song_id);
CREATE INDEX IF NOT EXISTS idx_songs_created_at ON songs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist);
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Functions
CREATE OR REPLACE FUNCTION increment_streams(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET streams = streams + 1 WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION increment_likes(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET likes = likes + 1 WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION decrement_likes(song_id INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE songs SET likes = GREATEST(likes - 1, 0) WHERE id = song_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username, email, created_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
    NEW.email,
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Row Level Security
ALTER TABLE likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view all likes" ON likes;
DROP POLICY IF EXISTS "Users can manage own likes" ON likes;
DROP POLICY IF EXISTS "Profiles are viewable by everyone" ON profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
DROP POLICY IF EXISTS "Songs are viewable by everyone" ON songs;
DROP POLICY IF EXISTS "Only admins can insert songs" ON songs;
DROP POLICY IF EXISTS "Only admins can update songs" ON songs;
DROP POLICY IF EXISTS "Only admins can delete songs" ON songs;

CREATE POLICY "Users can view all likes" ON likes FOR SELECT USING (true);
CREATE POLICY "Users can manage own likes" ON likes FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Profiles are viewable by everyone" ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Songs are viewable by everyone" ON songs FOR SELECT USING (true);

-- Note: Replace with your admin email
CREATE POLICY "Only admins can insert songs" ON songs
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND auth.jwt() ->> 'email' = 'YOUR_ADMIN_EMAIL@example.com');
CREATE POLICY "Only admins can update songs" ON songs
  FOR UPDATE USING (auth.uid() IS NOT NULL AND auth.jwt() ->> 'email' = 'YOUR_ADMIN_EMAIL@example.com');
CREATE POLICY "Only admins can delete songs" ON songs
  FOR DELETE USING (auth.uid() IS NOT NULL AND auth.jwt() ->> 'email' = 'YOUR_ADMIN_EMAIL@example.com');

