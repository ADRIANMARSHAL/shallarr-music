import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Initialize Supabase clients
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)