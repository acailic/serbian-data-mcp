"""WSGI entry point for production deployment (Render.com, etc).

Render runs: gunicorn wsgi:app
"""

import sys
from pathlib import Path

# Ensure src/ is importable before importing the Flask app
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_demo.app import app  # noqa: E402
