FROM python:3.11-slim

# make RUN behave like bash so ${var%.*} etc. work
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS="--max-old-space-size=64" \
    JULIA_NUM_THREADS=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      r-base nodejs npm golang default-jdk g++ make bash util-linux \
      ca-certificates curl gnupg xz-utils elfutils \
    && rm -rf /var/lib/apt/lists/*

# ---- Julia install (with execstack fix) ----
ARG JULIA_VERSION=1.10.5
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) julia_dir="x64";  julia_file_arch="x86_64" ;; \
      arm64) julia_dir="aarch64"; julia_file_arch="aarch64" ;; \
      *) echo "Unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    vshort="${JULIA_VERSION%.*}"; \
    curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${julia_dir}/${vshort}/julia-${JULIA_VERSION}-linux-${julia_file_arch}.tar.gz" -o /tmp/julia.tgz; \
    mkdir -p /opt; \
    tar -xzf /tmp/julia.tgz -C /opt; \
    ln -s "/opt/julia-${JULIA_VERSION}/bin/julia" /usr/local/bin/julia; \
    # clear execstack bit on libopenlibm if set
    eu-execstack -c "/opt/julia-${JULIA_VERSION}/lib/julia/libopenlibm.so" || true; \
    rm -f /tmp/julia.tgz

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# non-root
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
