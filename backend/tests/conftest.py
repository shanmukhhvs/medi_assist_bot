import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Tests never read the developer's backend/.env; they get a throwaway secret of valid length.
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-0123456789abcdef")
