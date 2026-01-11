# Production Dockerfile for Coolify deployment
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        libjpeg-dev \
        zlib1g-dev \
        curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY . .

# Build TypeScript modules
RUN chmod +x build.sh && ./build.sh

# Remove development artifacts for production
RUN find static/js -name "*.map" -type f -delete \
    && find static/js -name "*.d.ts" -type f -delete \
    && find static/js -name "*.d.ts.map" -type f -delete \
    && rm -rf static/js/village3d/tsconfig.json \
    && rm -rf static/js/tsconfig.json \
    && rm -rf node_modules \
    && rm -rf package*.json \
    && rm -rf tsconfig*.json \
    && rm -rf .git* \
    && rm -rf tests \
    && rm -rf test-results \
    && rm -rf playwright-report \
    && rm -f build.sh

RUN addgroup --system webwoelfe \
    && adduser --system --ingroup webwoelfe webwoelfe \
    && mkdir -p /app/instance \
    && mkdir -p /app/.cache \
    && chown -R webwoelfe:webwoelfe /app

USER webwoelfe

# Persistent volumes for Coolify deployment
VOLUME ["/app/instance", "/app/.cache"]

EXPOSE 5001

CMD ["gunicorn", \
     "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "--workers", "1", \
     "--worker-connections", "1000", \
     "--bind", "0.0.0.0:5001", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--capture-output", \
     "app:app"]