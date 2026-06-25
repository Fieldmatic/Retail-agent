from typing import TypedDict

from pydantic import BaseModel, ConfigDict

from agents.retail_analytics.schemas import RequestCategory


class RetailAgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    category: RequestCategory | None = None
    answer: str | None = None


class ClassificationUpdate(TypedDict):
    category: RequestCategory


class AnswerUpdate(TypedDict):
    answer: str
