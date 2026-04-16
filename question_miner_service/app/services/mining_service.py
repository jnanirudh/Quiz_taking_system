from app.config import Settings
from app.models import MiningJobResponse, PersistableQuestion
from app.services.ollama_client import OllamaClient
from app.services.pdf_extractor import PdfExtractor
from app.services.question_service_client import QuestionServiceClient


class QuestionMiningService:
    def __init__(
        self,
        *,
        settings: Settings,
        ollama_client: OllamaClient,
        question_service_client: QuestionServiceClient,
    ):
        self._settings = settings
        self._ollama_client = ollama_client
        self._question_service_client = question_service_client
        self._pdf_extractor = PdfExtractor()

    async def mine_pdf_to_questions(
        self,
        *,
        pdf_bytes: bytes,
        source_document_name: str,
        course_id: str,
        question_count: int,
        difficulty: str,
        teacher_id: str | None,
        persist: bool,
    ) -> MiningJobResponse:
        self._validate_pdf_size(pdf_bytes)
        extracted_text = self._pdf_extractor.extract_text(pdf_bytes)
        if not extracted_text:
            raise ValueError("No readable text could be extracted from the PDF")

        trimmed_text, was_truncated = self._trim_text(extracted_text)
        generated_questions = await self._ollama_client.generate_questions(
            course_id=course_id,
            difficulty=difficulty,
            question_count=question_count,
            document_text=trimmed_text,
        )

        persistable_questions = [
            PersistableQuestion(
                course_id=course_id,
                source_document_name=source_document_name,
                teacher_id=teacher_id,
                question_text=question.question_text,
                options=question.options,
                correct_option_index=question.correct_option_index,
                explanation=question.explanation,
                difficulty=question.difficulty,
                source_excerpt=question.source_excerpt,
            )
            for question in generated_questions
        ]

        persistence_mode_used = "skipped"
        persistence_results = []

        if persist:
            persistence_mode_used, persistence_results = await self._question_service_client.persist_questions(
                questions=persistable_questions
            )

        return MiningJobResponse(
            status="SUCCESS",
            message="Questions mined successfully from PDF",
            course_id=course_id,
            source_document_name=source_document_name,
            extracted_characters=len(trimmed_text),
            was_truncated=was_truncated,
            generated_questions_count=len(generated_questions),
            persisted_questions_count=len(persistable_questions) if persist else 0,
            persistence_mode_used=persistence_mode_used,
            questions=generated_questions,
            persistence_results=persistence_results,
        )

    def _validate_pdf_size(self, pdf_bytes: bytes) -> None:
        pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
        if pdf_size_mb > self._settings.pdf_max_size_mb:
            raise ValueError(
                f"PDF exceeds the allowed size of {self._settings.pdf_max_size_mb} MB"
            )

    def _trim_text(self, text: str) -> tuple[str, bool]:
        budget = self._settings.pdf_text_char_budget
        if len(text) <= budget:
            return text, False
        return text[:budget], True
