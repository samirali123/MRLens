import os
from dotenv import load_dotenv

load_dotenv()

RIVALS_API_KEY = os.getenv("RIVALS_API_KEY")
RIVALS_API_BASE_URL = os.getenv("RIVALS_API_BASE_URL", "https://marvelrivalsapi.com/api/v1")
RIVALS_API_BASE_URL_V2 = "https://marvelrivalsapi.com/api/v2"

DATABASE_URL = os.getenv("DATABASE_URL")

SCREEN_RESOLUTION = os.getenv("SCREEN_RESOLUTION", "1920x1080")
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_BASE = 2.0

_REQUIRED = {
    "RIVALS_API_KEY": RIVALS_API_KEY,
    "DATABASE_URL": DATABASE_URL,
}


def validate_env():
    missing = [k for k, v in _REQUIRED.items() if not v or v == "your_key_here"]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your keys."
        )


def get_api_headers() -> dict:
    return {
        "x-api-key": RIVALS_API_KEY,
        "Accept": "application/json",
    }
