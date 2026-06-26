FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NEWCOMER_AGENT_ROOT=/app
ENV SUBMISSION_FRONTEND_AGENT_TIMEOUT=300

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md ./
COPY app ./app
COPY submission_frontend ./submission_frontend

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "python -m uvicorn submission_frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
