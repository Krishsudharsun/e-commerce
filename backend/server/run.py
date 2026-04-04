import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
))

from flask import Flask
from flask_cors import CORS
from config.db import connect_db, get_db
from routes.auth     import auth_bp
from routes.products import products_bp
from routes.cart     import cart_bp
from routes.orders   import orders_bp
from routes.wishlist import wishlist_bp
from routes.payment  import payments_bp

app = Flask(__name__)
CORS(app,
     origins=["http://localhost:3000", "http://127.0.0.1:3000",
               "http://localhost:5500", "http://127.0.0.1:5500",
               "null", "*"],
     supports_credentials=True)

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
