from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


DifficultyLevel = Literal["EASY", "MEDIUM", "HARD"]


class GeneratedQuestion(BaseModel):
    question_text: str = Field(..., min_length=10, max_length=400)
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_option_index: int = Field(..., ge=0, le=3)
    explanation: str | None = Field(default=None, max_length=800)
    difficulty: DifficultyLevel = "MEDIUM"
    source_excerpt: str | None = Field(default=None, max_length=500)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str]) -> list[str]:
        cleaned = [option.strip() for option in value]
        if any(not option for option in cleaned):
            raise ValueError("Options must not be blank")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Options must be distinct")
        return cleaned


class OllamaQuestionEnvelope(BaseModel):
    questions: list[GeneratedQuestion] = Field(..., min_length=1)


class QuestionPersistResult(BaseModel):
    status_code: int
    response_body: Any


class MiningJobResponse(BaseModel):
    status: str
    message: str
    course_id: str
    source_document_name: str
    extracted_characters: int
    was_truncated: bool
    generated_questions_count: int
    persisted_questions_count: int
    persistence_mode_used: str
    questions: list[GeneratedQuestion]
    persistence_results: list[QuestionPersistResult] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service_suite: str
    service: str
    service_role: str
    ollama_model: str
    question_service_base_url: str


class PersistableQuestion(BaseModel):
    course_id: str
    source_document_name: str
    teacher_id: str | None = None
    question_text: str
    options: list[str]
    correct_option_index: int
    explanation: str | None = None
    difficulty: DifficultyLevel = "MEDIUM"
    source_excerpt: str | None = None

    @model_validator(mode="after")
    def validate_correct_option(self) -> "PersistableQuestion":
        if self.correct_option_index >= len(self.options):
            raise ValueError("Correct option index is out of range")
        return self
