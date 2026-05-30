#!/usr/bin/env python
import os
import traceback
import logging

from src.utils.database import get_validated_database_url_from_env, wait_for_database

try:
    from src import create_app
    db_url = get_validated_database_url_from_env()
    wait_for_database(
        db_url,
        timeout_seconds=int(os.environ.get("DB_STARTUP_TIMEOUT_SECONDS", "20")),
        interval_seconds=int(os.environ.get("DB_STARTUP_RETRY_INTERVAL_SECONDS", "2")),
    )
    app = create_app()
    logging.getLogger(__name__).info("Application created successfully")
except Exception as e:
    logging.getLogger(__name__).exception("Could not create application: %s", e)
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

