from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str = Field(alias="GOOGLE_API_KEY", min_length=1)
    gemini_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_MODEL")


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        fields = ", ".join(str(item["loc"][0]) for item in error.errors())
        raise RuntimeError(f"Set required environment variables in .env: {fields}") from error
