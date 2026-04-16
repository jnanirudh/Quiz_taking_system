from app.config import Settings, settings
from app.services.auth_client import AuthClient
from app.services.ollama_client import OllamaClient
from app.services.question_service_client import QuestionServiceClient
from app.services.mining_service import QuestionMiningService

_question_mining_service: QuestionMiningService | None = None


def set_question_mining_service(service: QuestionMiningService) -> None:
    global _question_mining_service
    _question_mining_service = service


def get_settings() -> Settings:
    return settings


def get_question_mining_service() -> QuestionMiningService:
    if _question_mining_service is None:
        raise RuntimeError("QuestionMiningService not initialised")
    return _question_mining_service


def build_question_mining_service(http_client, app_settings: Settings) -> QuestionMiningService:
    auth_client = AuthClient(http_client=http_client, settings=app_settings)
    return QuestionMiningService(
        settings=app_settings,
        ollama_client=OllamaClient(http_client=http_client, settings=app_settings),
        question_service_client=QuestionServiceClient(
            http_client=http_client,
            settings=app_settings,
            auth_client=auth_client,
        ),
    )
