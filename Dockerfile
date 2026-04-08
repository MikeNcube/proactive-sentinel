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
COPY start.sh .
RUN chmod +x start.sh

RUN useradd -m -u 1000 sentinel && chown -R sentinel:sentinel /app
USER sentinel

CMD ["sh", "start.sh"]
