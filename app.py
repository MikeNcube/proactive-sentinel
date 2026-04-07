#!/usr/bin/env python
import os
import traceback

try:
    from src import create_app
    app = create_app()
    print("SUCCESS: App created successfully", flush=True)
except Exception as e:
    print(f"FATAL ERROR: Could not create app: {e}", flush=True)
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
