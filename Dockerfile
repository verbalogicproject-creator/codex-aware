FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AWARE_DATABASE_PATH=/tmp/codex-aware/aware.db \
    PORT=8080

WORKDIR /app
COPY pyproject.toml README.md NOTICE ./
COPY services/api ./services/api
RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8080
CMD ["sh", "-c", "mkdir -p /tmp/codex-aware && exec uvicorn codex_aware.app:app --host 0.0.0.0 --port \"${PORT}\" --timeout-keep-alive 120"]
