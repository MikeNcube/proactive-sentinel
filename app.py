#!/usr/bin/env python
"""
Proactive Sentinel - Production entry point for Gunicorn
"""

import os

from src import create_app

# Create the application instance for Gunicorn
app = create_app()

if __name__ == "__main__":
    # Run locally for development
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
