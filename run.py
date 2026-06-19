"""
Portal 5 - CRM & Client Management
WSGI Entry Point

Usage:
    Development : python run.py
    Production  : gunicorn -w 4 -b 0.0.0.0:5050 "run:app"
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=debug)
