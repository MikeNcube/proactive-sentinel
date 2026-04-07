FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

RUN useradd -m -u 1000 sentinel && chown -R sentinel:sentinel /app
USER sentinel

CMD ["/bin/sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level debug app:app"]
