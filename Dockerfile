FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SMART_DISPATCH_HOST=0.0.0.0 \
    SMART_DISPATCH_PORT=8050 \
    SMART_DISPATCH_DB_PATH=/app/runtime-data/smart_dispatch.db \
    SMART_DISPATCH_LEARNING_STORE_PATH=/app/runtime-data/learning_store.runtime.json

WORKDIR /app

RUN python -m pip install --no-cache-dir \
    fastapi==0.138.2 \
    uvicorn==0.46.0 \
    pydantic==2.13.4 \
    sqlalchemy==2.0.51 \
    alembic==1.18.5

COPY alembic.ini pyproject.toml server.py ./
COPY app ./app
COPY frontend ./frontend
COPY data/learning_store.json ./data/learning_store.json
COPY data/seeds ./data/seeds

RUN mkdir -p /app/runtime-data

EXPOSE 8050

CMD ["python", "server.py"]
