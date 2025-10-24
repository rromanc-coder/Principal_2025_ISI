import os
from pathlib import Path

class Settings:
    APP_TITLE = "principal-isi"
    APP_VERSION = "1.5.0"

    WG_HOST = os.getenv("WG_HOST", "localhost")
    TEAMS_JSON = os.getenv("TEAMS_JSON", "[]")
    LOGO_UAEMEX_URL = os.getenv("LOGO_UAEMEX_URL", "").strip()
    LOGO_ING_URL = os.getenv("LOGO_ING_URL", "").strip()

    BASE_DIR = Path(__file__).resolve().parent
    STATIC_DIR = BASE_DIR / "static"

settings = Settings()
