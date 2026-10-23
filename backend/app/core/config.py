from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sports Court Booking API"
    app_env: str = "development"
    database_url: str = "mysql+pymysql://root@localhost:3306/sports_court_booking"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
