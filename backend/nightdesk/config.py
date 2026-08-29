from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CASES = Path(os.getenv("NIGHTDESK_CASES", ROOT / "sample_data" / "cases.json"))
DATA_DIR = Path(os.getenv("NIGHTDESK_DATA_DIR", ROOT / "data"))

APP_NAME = "nightdesk"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "nightdesk-shifts")
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "nightdesk")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

HOST = os.getenv("NIGHTDESK_HOST", "0.0.0.0")
PORT = int(os.getenv("NIGHTDESK_PORT", "43148"))


def google_cloud_project() -> str:
    """Empty unless the operator exports GOOGLE_CLOUD_PROJECT. No baked project id."""
    return (os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()


def use_vertex() -> bool:
    raw = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    return raw.lower() in {"1", "true", "yes"}


def has_adc() -> bool:
    """Real ADC only: existing credentials file or Cloud Run metadata. Not a project string."""
    creds = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if creds and Path(creds).is_file():
        return True
    if os.getenv("K_SERVICE"):
        return True
    return False


def has_gemini() -> bool:
    """Vertex + ADC. A project id or consumer API key does not mark the rail up."""
    return use_vertex() and has_adc()


def shift_token() -> str:
    """Shared secret for live shifts. Empty means POST /api/shifts is disabled."""
    return (os.getenv("SHIFT_TOKEN") or "").strip()


def shifts_enabled() -> bool:
    return bool(shift_token())

