FROM python:3.11-slim
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS="--max-old-space-size=64" \
    JULIA_NUM_THREADS=1

WORKDIR /app

# core runtimes + elfutils (eu-execstack)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      r-base \
      nodejs npm \
      golang \
      default-jdk \
      g++ make bash \
      util-linux \
      ca-certificates curl gnupg xz-utils elfutils \
    && rm -rf /var/lib/apt/lists/*

# ---- Julia tarball + clear execstack on ALL DSOs ----
ARG JULIA_VERSION=1.10.5
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) julia_dir="x64";  julia_file_arch="x86_64" ;; \
      arm64) julia_dir="aarch64"; julia_file_arch="aarch64" ;; \
      *) echo "Unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    vshort="${JULIA_VERSION%.*}"; \
    curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${julia_dir}/${vshort}/julia-${JULIA_VERSION}-linux-${julia_file_arch}.tar.gz" \
      -o /tmp/julia.tgz; \
    mkdir -p /opt; \
    tar -xzf /tmp/julia.tgz -C /opt; \
    ln -sf "/opt/julia-${JULIA_VERSION}/bin/julia" /usr/local/bin/julia; \
    # Clear execstack on any library requesting it (belt-and-suspenders)
    if command -v eu-execstack >/dev/null 2>&1; then \
      find "/opt/julia-${JULIA_VERSION}" -type f \( -name '*.so' -o -name '*.so.*' \) \
        -exec eu-execstack -c {} + || true; \
    fi; \
    rm -f /tmp/julia.tgz; \
    # ---- Self-test: fail the build if Julia still can’t start ----
    julia -e 'println("Julia OK: ", VERSION)'

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY main.py .

# non-root
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
