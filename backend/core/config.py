from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_PREFIX = "/api"
WEB_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
