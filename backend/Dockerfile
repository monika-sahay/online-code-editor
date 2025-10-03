FROM python:3.11-slim
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS="--max-old-space-size=64" \
    JULIA_NUM_THREADS=1

WORKDIR /app

# System deps (root)
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

# Create the runtime user BEFORE installing julia so we can install julia as this user
RUN useradd -ms /bin/bash appuser

# ---- Install Julia via juliaup AS appuser ----
USER appuser
# add juliaup path for this user
ENV PATH="/home/appuser/.juliaup/bin:${PATH}"
RUN curl -fsSL https://install.julialang.org | sh -s -- -y --default-channel 1.11
# Self-test so build fails early if julia isn't usable for appuser
RUN julia -e 'println("Julia OK via juliaup: ", VERSION)'

# ---- Back to root for Python deps ----
USER root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY main.py .

# Drop privileges for runtime
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
