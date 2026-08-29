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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "tarka-505801")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "nightdesk-shifts")
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "nightdesk")

# Vertex when explicitly requested; otherwise Gemini API (AI Studio key).
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in {"1", "true", "yes"}

HOST = os.getenv("NIGHTDESK_HOST", "0.0.0.0")
PORT = int(os.getenv("NIGHTDESK_PORT", "43148"))


def has_gemini() -> bool:
    if USE_VERTEX:
        return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_CLOUD_PROJECT"))
    return bool(GOOGLE_API_KEY)
