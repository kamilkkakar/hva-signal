from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process settings. Operator / server env only.

    Clients must never set these via header, query, or body. Request
    validation rejects those names. Defaults keep hosted live OFF and
    demo allowance closed. Do not put secrets in the repo.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    data_mode: str = "replay"
    log_level: str = "info"
    # Secret. Server env only. Never accept from a client. Never return.
    fortyguard_api_key: str = ""
    fortyguard_base_url: str = "https://api.fortyguard.com"
    api_public_url: str = "http://localhost:8000"
    web_public_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"
    cache_dir: str = ".cache/fortyguard"
    # Operator-only spend gate. Default closed. Not a client flag.
    demo_allowance_enabled: bool = False
    hva_public_two_signal: bool = False
    # RC-v2 analysis-area context. Default on. Set HVA_PUBLIC_CONTEXT=0 to disable.
    # Cache-only phoenix-demo. Does not enable hosted live or two-signal HTTP.
    hva_public_context: bool = True
    # Operator-only caps. Client cannot raise these.
    demo_allowance_max_total_units: int = 0
    demo_allowance_max_units_per_request: int = 1
    demo_allowance_allowed_areas: str = ""
    demo_allowance_valid_from: str = ""
    demo_allowance_valid_until: str = ""
    # Hosted live default OFF. Client cannot enable. Real vendor stays refused.
    hosted_live_enabled: bool = False
    hosted_live_real_vendor_enabled: bool = False
    # Operator approval is server-side only. Default denied.
    operator_approval_enabled: bool = False
    # Local file durability only. Default off. Enabling SQLite does not
    # enable hosted live, demo allowance, or any vendor adapter.
    local_sqlite_persistence_enabled: bool = False
    local_sqlite_path: str = ""
    demo_allowance_store_path: str = ""
    demo_allowance_reservation_ttl_seconds: int = 900
    demo_allowance_max_open_reservations: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
