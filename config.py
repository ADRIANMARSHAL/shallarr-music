# config.py
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    @classmethod
    def supabase(cls):
        return create_client(cls.SUPABASE_URL, cls.SUPABASE_KEY)
    
    @classmethod
    def supabase_admin(cls):
        return create_client(cls.SUPABASE_URL, cls.SUPABASE_SERVICE_KEY)
