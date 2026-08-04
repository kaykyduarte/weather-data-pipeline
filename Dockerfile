FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

RUN addgroup --system appgroup
RUN adduser --system --ingroup appgroup appuser

COPY --chown=appuser:appgroup src ./src

USER appuser

CMD ["python", "-m", "src.main"]