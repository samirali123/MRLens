import os
from dotenv import load_dotenv

load_dotenv()

RIVALS_API_KEY = os.getenv("RIVALS_API_KEY")
RIVALS_API_BASE_URL = os.getenv("RIVALS_API_BASE_URL", "https://marvelrivalsapi.com/api/v1")
RIVALS_API_BASE_URL_V2 = "https://marvelrivalsapi.com/api/v2"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")

SCREEN_RESOLUTION = os.getenv("SCREEN_RESOLUTION", "1920x1080")
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))

API_HEADERS = {
    "x-api-key": RIVALS_API_KEY,
    "Accept": "application/json",
}

RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_BASE = 2.0
