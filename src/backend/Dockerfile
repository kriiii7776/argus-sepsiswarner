FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (e.g., for psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt failed or missing, skipping"
# Fallback install if requirements.txt was empty/missing
RUN pip install fastapi uvicorn pydantic asyncpg psycopg2-binary redis

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
