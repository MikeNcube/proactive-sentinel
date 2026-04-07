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

# Run with migrations then gunicorn using Railway PORT (fallback 5001)
CMD ["sh", "-c", "python -m flask db upgrade && gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --timeout 120 app:app"]
