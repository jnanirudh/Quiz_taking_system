from dataclasses import dataclass
import os


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    service_suite_name: str = "Quiz System - FastAPI"
    service_name: str = "quiz-system-question-miner-service"
    service_role: str = "question-miner"
    service_host: str = os.getenv("QUESTION_MINER_HOST", "0.0.0.0")
    service_port: int = _int_env("QUESTION_MINER_PORT", 8010)

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "phi3:mini")
    ollama_timeout_seconds: int = _int_env("OLLAMA_TIMEOUT_SECONDS", 120)

    # --- Question-service (port 8081) ---
    question_service_base_url: str = os.getenv("QUESTION_SERVICE_BASE_URL", "http://127.0.0.1:8081")
    question_service_add_path: str = os.getenv("QUESTION_SERVICE_ADD_PATH", "/question/add")
    question_service_timeout_seconds: int = _int_env("QUESTION_SERVICE_TIMEOUT_SECONDS", 30)

    # --- Auth-service credentials for JWT auto-refresh (port 8080) ---
    auth_service_base_url: str = os.getenv("AUTH_SERVICE_BASE_URL", "http://127.0.0.1:8080")
    auth_service_admin_username: str | None = os.getenv("AUTH_SERVICE_ADMIN_USERNAME") or None
    auth_service_admin_password: str | None = os.getenv("AUTH_SERVICE_ADMIN_PASSWORD") or None

    pdf_max_size_mb: int = _int_env("PDF_MAX_SIZE_MB", 15)
    pdf_text_char_budget: int = _int_env("PDF_TEXT_CHAR_BUDGET", 18000)


settings = Settings()
