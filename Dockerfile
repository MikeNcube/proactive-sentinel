FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including bcrypt build deps
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements as root (critical -- not as appuser)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user AFTER pip install
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser . .

CMD ["sh", "-c", "python -m flask db upgrade && python seed.py && python -m flask run --host=0.0.0.0 --port=5001"]
