FROM python:3.11-slim

# Install system dependencies including FFmpeg, FFprobe, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . /app/

ENV PYTHONPATH=/app
ENV ALLOW_PAID_SERVICES=false
ENV DEV_MODE=false

CMD ["python", "-m", "orchestrator.orchestrator"]
