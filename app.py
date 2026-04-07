#!/usr/bin/env python
import os
import traceback
import logging

try:
    from src import create_app
    app = create_app()
    logging.getLogger(__name__).info("Application created successfully")
except Exception as e:
    logging.getLogger(__name__).exception("Could not create application: %s", e)
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
