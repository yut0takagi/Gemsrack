### Frontend build stage
FROM node:22-slim AS frontend-build

WORKDIR /work/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

### Backend runtime stage
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gemsrack ./gemsrack
COPY main.py .

# React build output (Vite) -> /app/web-dist
COPY --from=frontend-build /work/frontend/dist ./web-dist

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn -b :${PORT} -w 1 -k gthread --threads 8 --timeout 0 gemsrack.wsgi:app"]
