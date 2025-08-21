########## Stage 1: builder (installe les dépendances dans un venv) ##########
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG INSTALL_ML=false

COPY requirements-minimal.txt requirements-minimal.txt
COPY requirements-ml.txt requirements-ml.txt

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --prefer-binary -r requirements-minimal.txt \
    && if [ "$INSTALL_ML" = "true" ]; then /opt/venv/bin/pip install --no-cache-dir --prefer-binary -r requirements-ml.txt; fi \
    && find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} +

########## Stage 2: runtime ##########
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        PYTHONPATH="/app" \
        PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copier le venv uniquement
COPY --from=builder /opt/venv /opt/venv

# Copier le code (léger) après pour profiter du cache sur les deps
COPY . .

RUN mkdir -p /app/app/database

EXPOSE 8000

# Ensure correct line endings and executable bit for entrypoint
# Pre-install spaCy models for Presidio (fr/en) to improve NER recall
RUN python -m spacy download fr_core_news_sm && \
        python -m spacy download en_core_web_sm

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]