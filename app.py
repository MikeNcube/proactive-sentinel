import os
from src import create_app, db

app = create_app()


@app.route("/")
def home():
    return """
    <h1>Proactive Sentinel SOC Platform</h1>
    <p>✅ System is running successfully.</p>
    <p><a href="/login">Go to Login</a> | <a href="/dashboard">Go to Dashboard</a></p>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
