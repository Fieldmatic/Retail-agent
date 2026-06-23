from pydantic import BaseModel, ConfigDict


class RetailAgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str | None = None
