import os
from dotenv import load_dotenv

load_dotenv()

_supabase_client = None


def get_supabase():
    """Return the initialized Supabase client, creating it on first call."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in your .env file. "
            "See .env.example for reference."
        )

    from supabase import create_client
    _supabase_client = create_client(url, key)
    return _supabase_client
