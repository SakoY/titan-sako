from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Required — must be set in .env
    SECRET_KEY: str
    DATABASE_URL: str
    OL_BASE_URL: str

    # Static config — controls OL API concurrency
    OL_MAX_CONCURRENT_REQUESTS: int = 5


settings = Settings()
