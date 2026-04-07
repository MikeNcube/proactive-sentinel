import os

import redis
from flask_sqlalchemy import SQLAlchemy
try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover - optional in local/test envs
    class CORS:  # type: ignore[override]
        def init_app(self, app):
            return None

try:
    from flask_migrate import Migrate
except ImportError:  # pragma: no cover - optional in local/test envs
    class Migrate:  # type: ignore[override]
        def init_app(self, app, db):
            return None

# Database
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()

# Redis client - initialize lazily
redis_client = None


def get_redis():
    """Lazy initialization of Redis client."""
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client
