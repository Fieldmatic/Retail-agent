from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY", min_length=1)
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    use_vertex_ai: bool = Field(default=False, alias="USE_VERTEX_AI")
    vertex_ai_location: str = Field(default="us-central1", alias="VERTEX_AI_LOCATION")
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")

    @field_validator("google_cloud_project", mode="before")
    @classmethod
    def blank_project_is_missing(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_llm_provider(self) -> "Settings":
        if self.use_vertex_ai and self.google_cloud_project is None:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when USE_VERTEX_AI=true")
        if not self.use_vertex_ai and self.google_api_key is None:
            raise ValueError("GOOGLE_API_KEY is required when USE_VERTEX_AI=false")
        return self


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        fields = ", ".join(str(item["loc"][0]) for item in error.errors())
        raise RuntimeError(f"Set required environment variables in .env: {fields}") from error
