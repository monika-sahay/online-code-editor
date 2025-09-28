FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (add r-base)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    r-base \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]

# (Optional) Preinstall useful R packages
# RUN R -q -e 'install.packages(c("ggplot2","dplyr"), repos="https://cloud.r-project.org")'

