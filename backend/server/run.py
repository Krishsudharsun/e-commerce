import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
))

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from config.db import connect_db, get_db
from routes.auth     import auth_bp
from routes.products import products_bp
from routes.cart     import cart_bp
from routes.orders   import orders_bp
from routes.wishlist import wishlist_bp
from routes.payment  import payments_bp

app = Flask(__name__)

# Allow all origins — tightened per-route in production
CORS(app, supports_credentials=True, origins="*")


# ── Intercept every OPTIONS preflight and return 200 immediately ──────────────
# Browsers send OPTIONS before every cross-origin POST/PUT/DELETE.
# If Flask doesn't respond with CORS headers, the real request is never sent.
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"]      = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization, ngrok-skip-browser-warning"
        response.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"]           = "3600"
        response.status_code = 200
        return response


# ── Inject CORS headers on every response (including 4xx / 5xx) ──────────────
@app.after_request
def apply_cors(response):
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"]      = origin
    response.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization, ngrok-skip-browser-warning"
    response.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# ── Catch all unhandled exceptions — return JSON so CORS headers are applied ──
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    response = jsonify({"error": "Internal server error", "detail": str(e)})
    response.status_code = 500
    return response
# ─────────────────────────────────────────────────────────────────────────────


app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(wishlist_bp)
app.register_blueprint(payments_bp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "E-Commerce API running"}, 200


def seed_products():
    db = get_db()
    if db.products.count_documents({}) > 0:
        return
    sample = [
        {"name": "Wireless Headphones", "price": 79.99,  "description": "Noise-cancelling over-ear headphones.", "image": "🎧", "category": "Electronics",  "stock": 50},
        {"name": "Running Sneakers",    "price": 59.99,  "description": "Lightweight mesh sneakers.",            "image": "👟", "category": "Footwear",     "stock": 30},
        {"name": "Leather Wallet",      "price": 29.99,  "description": "Slim RFID-blocking bifold wallet.",     "image": "👜", "category": "Accessories",  "stock": 100},
        {"name": "Smart Watch",         "price": 149.99, "description": "Fitness tracker with GPS.",             "image": "⌚", "category": "Electronics",  "stock": 20},
        {"name": "Sunglasses",          "price": 39.99,  "description": "Polarised UV400 aviator sunglasses.",   "image": "🕶️","category": "Accessories",  "stock": 60},
        {"name": "Backpack",            "price": 49.99,  "description": "30L waterproof hiking backpack.",       "image": "🎒", "category": "Bags",         "stock": 40},
        {"name": "Coffee Maker",        "price": 89.99,  "description": "12-cup programmable drip coffee maker.","image": "☕", "category": "Kitchen",      "stock": 25},
        {"name": "Yoga Mat",            "price": 24.99,  "description": "Non-slip 6mm TPE yoga mat.",           "image": "🧘", "category": "Sports",       "stock": 80},
    ]
    db.products.insert_many(sample)
    print(f"Seeded {len(sample)} sample products.")


def seed_admin():
    """
    Creates a default admin account on first startup if none exists.
    Set ADMIN_EMAIL and ADMIN_PASSWORD in .env to change the defaults.
    """
    db             = get_db()
    admin_email    = os.getenv("ADMIN_EMAIL",    "admin@freshmart.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    if db.users.find_one({"role": "admin"}):
        return

    import bcrypt
    from datetime import datetime
    hashed = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
    db.users.insert_one({
        "name":              "Admin",
        "email":             admin_email,
        "password_hash":     hashed,
        "role":              "admin",
        "phone":             "",
        "primary_address":   {},
        "secondary_address": {},
        "created_at":        datetime.utcnow(),
        "updated_at":        datetime.utcnow(),
    })
    print(f"Admin account created: {admin_email}")
    print("  Change credentials via ADMIN_EMAIL / ADMIN_PASSWORD in .env")


if __name__ == "__main__":
    connect_db()
    seed_products()
    seed_admin()
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)