# Quiz System - FastAPI Question Miner Service

`question_miner_service` is a standalone FastAPI microservice that:

1. Accepts a course PDF from a teacher.
2. Extracts readable text from the PDF.
3. Sends that content to a local Ollama model to generate MCQs.
4. Pushes the generated questions into an existing question CRUD service.

## Microservice Boundary

This service is intentionally limited to orchestration responsibilities:

- Owns PDF ingestion and text extraction.
- Owns LLM prompting and response validation.
- Does not own question persistence logic.
- Does not perform direct DB CRUD.
- Delegates question creation to the existing Spring Boot question service.

That separation keeps the architecture clean:

- `question_miner_service`: AI workflow and document processing.
- Spring Boot question service: database-backed question CRUD.
- Eye proctoring service: exam monitoring and gaze analysis.

## API

### `GET /health`

Returns service health and configured downstream targets.

### `POST /mining/questions/from-pdf`

Accepts `multipart/form-data`:

- `file`: PDF document
- `course_id`: target course identifier
- `question_count`: desired number of questions
- `difficulty`: optional, defaults to `MEDIUM`
- `teacher_id`: optional
- `persist`: optional, defaults to `true`

Example using `curl`:

```bash
curl -X POST http://127.0.0.1:8010/mining/questions/from-pdf \
  -F "file=@/absolute/path/to/course-notes.pdf" \
  -F "course_id=cs101" \
  -F "question_count=10" \
  -F "difficulty=MEDIUM" \
  -F "teacher_id=t42"
```

## Expected Question Service Contract

By default the miner tries:

1. `POST {QUESTION_SERVICE_BASE_URL}{QUESTION_SERVICE_BULK_CREATE_PATH}`
2. If bulk mode is enabled and the bulk endpoint returns `404` or `405`, it falls back to single creates with:
   `POST {QUESTION_SERVICE_BASE_URL}{QUESTION_SERVICE_SINGLE_CREATE_PATH}`

Default bulk payload:

```json
{
  "courseId": "cs101",
  "teacherId": "t42",
  "sourceDocumentName": "course-notes.pdf",
  "questions": [
    {
      "questionText": "What does ... ?",
      "difficulty": "MEDIUM",
      "explanation": "Because ...",
      "sourceExcerpt": "Relevant line from the PDF",
      "options": [
        { "text": "Option A", "isCorrect": false },
        { "text": "Option B", "isCorrect": true },
        { "text": "Option C", "isCorrect": false },
        { "text": "Option D", "isCorrect": false }
      ]
    }
  ]
}
```

Default single-create payload:

```json
{
  "courseId": "cs101",
  "teacherId": "t42",
  "sourceDocumentName": "course-notes.pdf",
  "questionText": "What does ... ?",
  "difficulty": "MEDIUM",
  "explanation": "Because ...",
  "sourceExcerpt": "Relevant line from the PDF",
  "options": [
    { "text": "Option A", "isCorrect": false },
    { "text": "Option B", "isCorrect": true },
    { "text": "Option C", "isCorrect": false },
    { "text": "Option D", "isCorrect": false }
  ]
}
```

If your Spring Boot service expects a different payload shape, update the client mapping in:

- `question_miner_service/app/services/question_service_client.py`

## Configuration

Copy `.env.example` values into your environment or export them directly.

Key variables:

- `QUESTION_MINER_HOST`
- `QUESTION_MINER_PORT`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `QUESTION_SERVICE_BASE_URL`
- `QUESTION_SERVICE_BULK_CREATE_PATH`
- `QUESTION_SERVICE_SINGLE_CREATE_PATH`
- `QUESTION_SERVICE_MODE`
- `QUESTION_SERVICE_AUTH_TOKEN`

## Local Run

```bash
cd question_miner_service
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Interactive docs:

`http://127.0.0.1:8010/docs`

## Ollama Setup

If Ollama is not already running locally:

```bash
ollama serve
ollama pull llama3.1:8b
```

Then export:

```bash
export OLLAMA_MODEL=llama3.1:8b
export OLLAMA_BASE_URL=http://127.0.0.1:11434
```

## Notes

- The service truncates very large extracted PDFs before sending them to the model.
- `persist=false` lets you validate generation without calling the question CRUD service.
- This service is additive and does not change the existing eye proctoring app.
- The FastAPI app title is `Quiz System - FastAPI Question Miner Service` so it is clearly distinguished in Swagger/OpenAPI.
