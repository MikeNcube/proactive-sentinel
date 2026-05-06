#!/bin/sh
set -e
echo "=== Starting Proactive Sentinel ==="
echo "=== Creating database tables directly ==="
python -c "
from src import create_app
from src.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created successfully')
"
echo "=== Seeding database ==="
python seed.py
echo "=== Starting Gunicorn ==="
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info app:app
