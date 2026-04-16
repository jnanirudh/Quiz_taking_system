from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import build_question_mining_service, set_question_mining_service
from app.routers import mining


@asynccontextmanager
async def lifespan(_: FastAPI):
    timeout = httpx.Timeout(
        connect=min(settings.question_service_timeout_seconds, settings.ollama_timeout_seconds),
        read=max(settings.question_service_timeout_seconds, settings.ollama_timeout_seconds),
        write=max(settings.question_service_timeout_seconds, settings.ollama_timeout_seconds),
        pool=max(settings.question_service_timeout_seconds, settings.ollama_timeout_seconds),
    )
    async with httpx.AsyncClient(timeout=timeout) as http_client:
        set_question_mining_service(build_question_mining_service(http_client, settings))
        yield


app = FastAPI(
    title="Quiz System - FastAPI Question Miner Service",
    description=(
        "Question-miner microservice for the Quiz System. "
        "It extracts MCQs from PDFs using a local Ollama model and forwards them "
        "to the question CRUD service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mining.router)
