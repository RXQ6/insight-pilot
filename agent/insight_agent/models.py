from pydantic import BaseModel, Field


class TaskMessage(BaseModel):
    taskId: str
    sessionId: str
    userId: str
    message: str
    model: str | None = None
    maxSteps: int = Field(default=8, ge=1, le=20)
    costCapCny: float = Field(default=0.2, ge=0.0)
    history: str = ""
    createdAt: str | None = None


class ResultEvent(BaseModel):
    taskId: str
    type: str
    content: str | dict | None = None
    ts: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    status: str = "pending"
    output: str | None = None
    error: str | None = None
