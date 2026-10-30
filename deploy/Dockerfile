FROM node:22-alpine AS web
WORKDIR /build
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run check && npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/apps/api DATA_DIR=/data COOKIE_SECURE=true LLM_ENABLED=false
WORKDIR /app
COPY deploy/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 --home /app evidence
COPY apps/api/ apps/api/
COPY datasets/demo/ datasets/demo/
COPY --from=web /build/dist/ apps/web/dist/
RUN mkdir /data && chown evidence:evidence /data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2)" || exit 1
CMD ["uvicorn","evidencerag.main:app","--host","0.0.0.0","--port","8000","--workers","1","--limit-concurrency","8","--timeout-keep-alive","5","--no-access-log","--no-proxy-headers"]
