import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from config.db import connect_db, get_db
from routes.auth import auth_bp
from routes.products import products_bp
from routes.cart import cart_bp
from routes.orders import orders_bp
from routes.wishlist import wishlist_bp

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "null", "*"],
     supports_credentials=True)

app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(wishlist_bp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "E-Commerce API running 🚀"}, 200


def seed_products():
    db = get_db()
    if db.products.count_documents({}) > 0:
        return
    sample = [
        {"name": "Wireless Headphones", "price": 79.99, "description": "Noise-cancelling over-ear headphones with 30hr battery.", "image": "🎧", "category": "Electronics", "stock": 50},
        {"name": "Running Sneakers",    "price": 59.99, "description": "Lightweight breathable mesh sneakers for daily runs.",     "image": "👟", "category": "Footwear",    "stock": 30},
        {"name": "Leather Wallet",      "price": 29.99, "description": "Slim genuine leather bifold wallet with RFID blocking.",   "image": "👜", "category": "Accessories", "stock": 100},
        {"name": "Smart Watch",         "price": 149.99,"description": "Fitness tracker with heart rate monitor and GPS.",         "image": "⌚", "category": "Electronics", "stock": 20},
        {"name": "Sunglasses",          "price": 39.99, "description": "Polarised UV400 protection aviator sunglasses.",           "image": "🕶️","category": "Accessories", "stock": 60},
        {"name": "Backpack",            "price": 49.99, "description": "30L waterproof hiking backpack with laptop sleeve.",       "image": "🎒", "category": "Bags",        "stock": 40},
        {"name": "Coffee Maker",        "price": 89.99, "description": "12-cup programmable drip coffee maker with timer.",        "image": "☕", "category": "Kitchen",     "stock": 25},
        {"name": "Yoga Mat",            "price": 24.99, "description": "Non-slip 6mm TPE eco-friendly yoga mat.",                  "image": "🧘", "category": "Sports",      "stock": 80},
    ]
    db.products.insert_many(sample)
    print(f"🌱 Seeded {len(sample)} sample products.")


if __name__ == "__main__":
    connect_db()
    seed_products()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🚀 Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)