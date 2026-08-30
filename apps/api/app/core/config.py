from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    data_mode: str = "replay"
    log_level: str = "info"
    fortyguard_api_key: str = ""
    fortyguard_base_url: str = "https://api.fortyguard.com"
    api_public_url: str = "http://localhost:8000"
    web_public_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"
    cache_dir: str = ".cache/fortyguard"
    demo_allowance_enabled: bool = False
    hva_public_two_signal: bool = False
    demo_allowance_max_total_units: int = 0
    demo_allowance_max_units_per_request: int = 1
    demo_allowance_allowed_areas: str = ""
    demo_allowance_valid_from: str = ""
    demo_allowance_valid_until: str = ""
    # Local file durability only. Default off. Enabling SQLite does not
    # enable hosted live, demo allowance, or any vendor adapter.
    local_sqlite_persistence_enabled: bool = False
    local_sqlite_path: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
