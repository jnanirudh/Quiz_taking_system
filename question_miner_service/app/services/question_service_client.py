"""question_service_client.py — pushes generated questions to the Java Question-service.

Key design decisions
--------------------
• Endpoint  : POST /question/add  (the only write endpoint exposed by QuestionController)
• Payload   : flat Java schema — questionTitle, option1-4, rightAnswer, difficultyLevel, subject
• Auth token: obtained from AuthClient (auto-refreshes before expiry; see auth_client.py)
• One-by-one: the Java service has no bulk endpoint, so each question is posted individually.
              On the first 401 the token is force-refreshed and the request is retried once.
"""
from __future__ import annotations

import httpx

from app.config import Settings
from app.models import PersistableQuestion, QuestionPersistResult
from app.services.auth_client import AuthClient


class QuestionServiceClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings: Settings,
        auth_client: AuthClient,
    ) -> None:
        self._http = http_client
        self._settings = settings
        self._auth = auth_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def persist_questions(
        self,
        *,
        questions: list[PersistableQuestion],
    ) -> tuple[str, list[QuestionPersistResult]]:
        """Send every question to POST /question/add and return results."""
        results: list[QuestionPersistResult] = []
        for question in questions:
            result = await self._post_question(question)
            results.append(result)
        return "single", results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _post_question(
        self, question: PersistableQuestion, *, _retry: bool = True
    ) -> QuestionPersistResult:
        """POST one question; retries once on 401 after forcing a token refresh."""
        token = await self._auth.get_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        response = await self._http.post(
            self._build_url(self._settings.question_service_add_path),
            json=self._to_java_payload(question),
            headers=headers,
            timeout=self._settings.question_service_timeout_seconds,
        )

        # On 401 → force a token refresh and retry exactly once
        if response.status_code == 401 and _retry:
            self._auth._expires_at = 0.0  # force stale so _refresh() runs
            return await self._post_question(question, _retry=False)

        response.raise_for_status()
        return QuestionPersistResult(
            status_code=response.status_code,
            response_body=self._safe_body(response),
        )

    def _to_java_payload(self, question: PersistableQuestion) -> dict:
        """Convert the Python nested schema to the flat Java Question entity fields.

        Java Question entity columns:
            questionTitle, subject, marks,
            option1, option2, option3, option4,
            rightAnswer, difficultyLevel
        """
        options = question.options  # always exactly 4 strings (validated by Pydantic)
        return {
            "questionTitle": question.question_text,
            # Use course_id as the subject so Quiz-service can query by subject
            "subject": question.course_id,
            "marks": 1,
            "option1": options[0],
            "option2": options[1],
            "option3": options[2],
            "option4": options[3],
            # rightAnswer is the literal text of the correct option
            "rightAnswer": options[question.correct_option_index],
            "difficultyLevel": question.difficulty,
        }

    def _build_url(self, path: str) -> str:
        return f"{self._settings.question_service_base_url.rstrip('/')}/{path.lstrip('/')}"

    def _safe_body(self, response: httpx.Response):
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text
