# API server + dashboard. The video pipeline runs elsewhere and posts events to /api/ingest.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt
COPY roadsentinel/ roadsentinel/
COPY web/ web/
COPY cameras/ cameras/
CMD ["sh", "-c", "uvicorn roadsentinel.server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
