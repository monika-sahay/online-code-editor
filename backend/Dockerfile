# Multi-runtime FastAPI runner (Render-friendly, no nested containers)
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Core OS deps + runtimes available from Debian trixie
# - r-base: R + Rscript
# - nodejs npm: JavaScript runtime
# - golang: Go toolchain
# - default-jdk: will install OpenJDK (21 on trixie)
# - g++ make bash: compilers & shell
# - util-linux: provides 'prlimit' to cap CPU/memory per process
# - ca-certificates curl gnupg xz-utils: basics + for Julia install
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

# ---- Install Julia from official tarball (Debian trixie has no 'julia' pkg) ----
# Choose a stable Julia version; update as needed.
ARG JULIA_VERSION=1.10.5
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) julia_arch="x86_64";; \
      arm64) julia_arch="aarch64";; \
      *) echo "Unsupported arch: $arch" && exit 1;; \
    esac; \
    curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${julia_arch:0:1}${julia_arch}/$JULIA_VERSION/julia-$JULIA_VERSION-linux-$julia_arch.tar.gz" -o /tmp/julia.tgz; \
    mkdir -p /opt; \
    tar -xzf /tmp/julia.tgz -C /opt; \
    ln -s "/opt/julia-$JULIA_VERSION/bin/julia" /usr/local/bin/julia; \
    rm -f /tmp/julia.tgz

# (Optional) Preinstall useful R/Python packages to speed first-run
# RUN R -q -e 'install.packages(c("ggplot2","dplyr"), repos="https://cloud.r-project.org")'

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY main.py .

# ---- Run as non-root for safety ----
RUN useradd -ms /bin/bash appuser
USER appuser

# Render will inject $PORT. Default 8000 for local runs.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
