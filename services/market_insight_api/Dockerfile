FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ pipeline/
COPY services/market_insight_api/ services/market_insight_api/

ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data
ENV DUCKDB_PATH=/app/data/warehouse.duckdb

EXPOSE 8081
CMD ["uvicorn", "services.market_insight_api.main:app", "--host", "0.0.0.0", "--port", "8081"]
