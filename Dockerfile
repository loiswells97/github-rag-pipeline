FROM python:3.12-slim-bookworm

WORKDIR /app
RUN pip install --no-cache-dir uv fastapi uvicorn

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
COPY main.py query.py ingest.py parsing.py log.py db_setup.py ./
EXPOSE 80
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]