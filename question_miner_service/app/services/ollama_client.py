import json

import httpx

from app.config import Settings
from app.models import DifficultyLevel, GeneratedQuestion, OllamaQuestionEnvelope


class OllamaClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self._http_client = http_client
        self._settings = settings

    async def generate_questions(
        self,
        *,
        course_id: str,
        difficulty: DifficultyLevel,
        question_count: int,
        document_text: str,
    ) -> list[GeneratedQuestion]:
        prompt = self._build_prompt(
            course_id=course_id,
            difficulty=difficulty,
            question_count=question_count,
            document_text=document_text,
        )

        response = await self._http_client.post(
            f"{self._settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self._settings.ollama_model,
                "stream": False,
                "format": "json",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You generate high-quality academic MCQs from course material. "
                            "Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self._settings.ollama_timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        content = data.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("Ollama returned an empty response")

        payload = self._load_json(content)
        envelope = OllamaQuestionEnvelope.model_validate(payload)
        questions = envelope.questions[:question_count]

        if len(questions) < question_count:
            raise ValueError(
                f"Ollama returned {len(questions)} questions, but {question_count} were requested"
            )

        return questions

    def _build_prompt(
        self,
        *,
        course_id: str,
        difficulty: DifficultyLevel,
        question_count: int,
        document_text: str,
    ) -> str:
        return f"""
Generate exactly {question_count} multiple-choice questions from the course material below.

Requirements:
- Course id: {course_id}
- Difficulty: {difficulty}
- Each question must have exactly 4 answer options.
- Exactly one option is correct.
- Avoid ambiguous or opinion-based questions.
- Use only facts supported by the provided material.
- Keep explanations concise.
- Add a short source_excerpt copied from the material that justifies the answer.

Return JSON with this exact schema:
{{
  "questions": [
    {{
      "question_text": "string",
      "options": ["string", "string", "string", "string"],
      "correct_option_index": 0,
      "explanation": "string",
      "difficulty": "{difficulty}",
      "source_excerpt": "string"
    }}
  ]
}}

Course material:
\"\"\"
{document_text}
\"\"\"
""".strip()

    def _load_json(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or start >= end:
                raise ValueError("Ollama response was not valid JSON") from None
            return json.loads(content[start : end + 1])
