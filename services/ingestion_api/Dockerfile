FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schemas/ schemas/
COPY validation/ validation/
COPY pipeline/ pipeline/
COPY services/ingestion_api/ services/ingestion_api/
COPY dbt/seeds/ dbt/seeds/

ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data
ENV DUCKDB_PATH=/app/data/warehouse.duckdb

EXPOSE 8080
CMD ["uvicorn", "services.ingestion_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
