from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./allergy_scan.db"
    haccp_service_key: str = ""
    food_safety_api_key: str = ""
    google_vision_api_key: str = ""
    openfoodfacts_user_agent: str = "AllergyScan/1.0 (contact@example.com)"
    ocr_confidence_threshold: float = 0.65

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
