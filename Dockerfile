FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_PROVIDER=gemini \
    ENABLE_CROSS_ENCODER=false \
    DATA_DIR=/app/data

WORKDIR /app

RUN groupadd --system resolveiq \
    && useradd --system --gid resolveiq --home-dir /app resolveiq

COPY requirements-render.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-render.txt

COPY app.py ./
COPY backend ./backend

RUN mkdir -p /app/data \
    && chown -R resolveiq:resolveiq /app

USER resolveiq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
