from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.config import get_settings
from tokentoll.crypto import load_or_generate_private_key
from tokentoll.database import get_db
from tokentoll.schemas.challenge import (
    ChallengeRequest,
    ChallengeResponse,
    QuestionOut,
    VerifyRequest,
    VerifyResponse,
)
from tokentoll.services.challenge_service import create_challenge
from tokentoll.services.verify_service import verify_challenge


router = APIRouter(tags=["challenges"])


@router.post("/challenge", response_model=ChallengeResponse, status_code=201)
async def request_challenge(
    body: ChallengeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChallengeResponse:
    ip_address = request.client.host if request.client else None
    try:
        challenge, generated = await create_challenge(
            db, body.site_key, ip_address
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_or_inactive_site_key"},
        ) from exc

    return ChallengeResponse(
        challenge_id=str(challenge.id),
        context=generated.context,
        questions=[
            QuestionOut(
                id=question.id,
                text=question.text,
                answer_format=question.answer_format,
            )
            for question in generated.questions
        ],
        expires_at=challenge.expires_at.isoformat(),
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_answers(
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    settings = get_settings()
    private_key = load_or_generate_private_key(settings.rsa_private_key_path)
    result = await verify_challenge(
        db=db,
        challenge_id=body.challenge_id,
        nonce=body.nonce,
        answers=body.answers,
        commitment=body.commitment,
        private_key=private_key,
    )
    return VerifyResponse(**result)
