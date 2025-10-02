FROM python:3.11-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS="--max-old-space-size=64" \
    JULIA_NUM_THREADS=1

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      r-base \
      nodejs npm \
      golang \
      default-jdk \
      g++ make bash \
      util-linux \
      ca-certificates curl gnupg xz-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Julia via juliaup ----
RUN curl -fsSL https://install.julialang.org | sh -s -- -y --default-channel 1.11
ENV PATH="/root/.juliaup/bin:${PATH}"

# Self-test Julia install
RUN julia -e 'println("Julia OK via juliaup: ", VERSION)'

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY main.py .

# Create non-root user
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

