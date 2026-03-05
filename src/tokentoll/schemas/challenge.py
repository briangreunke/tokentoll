from __future__ import annotations

from pydantic import BaseModel, Field


class ChallengeRequest(BaseModel):
    site_key: str = Field(min_length=1)


class QuestionOut(BaseModel):
    id: str
    text: str
    answer_format: str


class ChallengeResponse(BaseModel):
    challenge_id: str
    context: str
    questions: list[QuestionOut]
    expires_at: str


class VerifyRequest(BaseModel):
    challenge_id: str
    nonce: str
    answers: dict[str, str]
    commitment: str


class VerifyResponse(BaseModel):
    success: bool
    token: str | None = None
    score: float | None = None
    error: str | None = None
