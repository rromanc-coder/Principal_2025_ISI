from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_TITLE: str = "principal-isi"
    APP_VERSION: str = "1.5.0"

    # Monitor & logos
    WG_HOST: str = "localhost"
    TEAMS_JSON: str = "[]"
    LOGO_UAEMEX_URL: str = ""
    LOGO_ING_URL: str = ""

    BASE_DIR: Path = Path(__file__).resolve().parent
    STATIC_DIR: Path = BASE_DIR / "static"

    class Config:
        case_sensitive = False

settings = Settings()
