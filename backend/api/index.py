import os
import sys

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set VERCEL environment variable and safe fallback database URL
os.environ["VERCEL"] = "1"
if not os.environ.get("DATABASE_URL") or "localhost" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/social_commerce.db"

from app.main import app
