import sys
import os

# Allow imports from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from config.db import connect_db
from routes.auth import auth_bp
from routes.products import products_bp

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)
# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "E-Commerce API is running 🚀"}, 200


if __name__ == "__main__":
    connect_db()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🚀 Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)