import os

import redis
from flask_sqlalchemy import SQLAlchemy
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - optional in local/test envs
    class Limiter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            return None

        def limit(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    def get_remote_address():  # type: ignore[return-value]
        return "127.0.0.1"
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
redis_url = os.environ.get("REDIS_URL", None)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url if redis_url else "memory://",
    default_limits=["1000 per hour"],
)

# Redis client - initialize lazily
redis_client = None


def get_redis():
    """Lazy initialization of Redis client."""
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client
