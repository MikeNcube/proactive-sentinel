FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 sentinel && chown -R sentinel:sentinel /app
USER sentinel

# Expose port (Railway provides PORT env variable)
EXPOSE $PORT

# Run gunicorn in shell so ${PORT} expands correctly
CMD ["/bin/sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2"]
