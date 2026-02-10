FROM python:3.12-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY alembic.ini .
COPY alembic/ alembic/
COPY scripts/ scripts/
COPY src/ src/

# Run migrations then start the bot
CMD ["sh", "-c", "python -m scripts.init_db && python -m src.main"]
