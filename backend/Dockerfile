# backend/Dockerfile
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtimes + tools:
# - r-base (R)
# - nodejs npm (JS)
# - golang (Go)
# - julia (Julia)
# - openjdk-17-jdk (Java compile+run)
# - g++ make bash (C/C++ compile)
# - util-linux (prlimit)
# - ca-certificates curl gnupg (utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
      r-base \
      nodejs npm \
      golang \
      julia \
      openjdk-17-jdk \
      g++ make bash \
      util-linux \
      ca-certificates curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY main.py .

# Non-root
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
