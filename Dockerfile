# Cloud Run image: Next.js static console + FastAPI agent.
# Scale to zero. Do not bake GOOGLE_API_KEY into the image.

FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV NIGHTDESK_EXPORT=1
ENV NEXT_PUBLIC_API_URL=same-origin
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    NIGHTDESK_STATIC=/app/web/out \
    NIGHTDESK_HOST=0.0.0.0 \
    NIGHTDESK_PORT=8080 \
    GEMINI_MODEL=gemini-3.5-flash

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY sample_data /app/sample_data
COPY --from=web /web/out /app/web/out

EXPOSE 8080
CMD ["python", "-m", "nightdesk"]
