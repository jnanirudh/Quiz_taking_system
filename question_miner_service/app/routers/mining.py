from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings
from app.dependencies import get_question_mining_service, get_settings
from app.models import HealthResponse, MiningJobResponse
from app.services.mining_service import QuestionMiningService

router = APIRouter(tags=["Question Mining"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service_suite=settings.service_suite_name,
        service=settings.service_name,
        service_role=settings.service_role,
        ollama_model=settings.ollama_model,
        question_service_base_url=settings.question_service_base_url,
    )


@router.post("/mining/questions/from-pdf", response_model=MiningJobResponse)
async def mine_questions_from_pdf(
    file: UploadFile = File(...),
    course_id: str = Form(...),
    question_count: int = Form(..., ge=1, le=50),
    difficulty: str = Form("MEDIUM"),
    teacher_id: str | None = Form(default=None),
    persist: bool = Form(default=True),
    service: QuestionMiningService = Depends(get_question_mining_service),
) -> MiningJobResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    difficulty = difficulty.upper()
    if difficulty not in {"EASY", "MEDIUM", "HARD"}:
        raise HTTPException(status_code=400, detail="difficulty must be EASY, MEDIUM, or HARD")

    try:
        pdf_bytes = await file.read()
        return await service.mine_pdf_to_questions(
            pdf_bytes=pdf_bytes,
            source_document_name=file.filename,
            course_id=course_id,
            question_count=question_count,
            difficulty=difficulty,
            teacher_id=teacher_id,
            persist=persist,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service call failed: {exc}") from exc
