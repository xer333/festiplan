from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FestiPlan"
    database_url: str = "sqlite:///./festiplan.db"
    fail_notifications: bool = False
    model_config = SettingsConfigDict(env_prefix="FESTIPLAN_", env_file=".env", extra="ignore")
settings = Settings()
