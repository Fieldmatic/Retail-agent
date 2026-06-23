import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    google_api_key: str = Field(min_length=1)
    gemini_model: str = "gemini-2.5-flash"


def load_settings() -> Settings:
    load_dotenv()

    try:
        return Settings(
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
    except ValidationError as error:
        raise RuntimeError("Set GOOGLE_API_KEY in .env before asking questions.") from error
