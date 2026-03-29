import sys
import os
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from config.db import connect_db, get_db
from routes.auth import auth_bp
from routes.products import products_bp, admin_bp
from routes.cart import cart_bp
from routes.orders import orders_bp
from routes.wishlist import wishlist_bp

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "null", "*"],
     supports_credentials=True)

app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(admin_bp)
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
        {"name": "Fresh Mint",        "price": 1.00,  "description": "Fresh mint bunch, good quality.", "image": "🌿", "category": "Vegetables", "stock": 100},
        {"name": "Fresh Coriander",   "price": 1.00,  "description": "Fresh coriander bunch.",          "image": "🌿", "category": "Vegetables", "stock": 100},
        {"name": "Fresh Potato",      "price": 10.00, "description": "Farm fresh potatoes, 1kg.",       "image": "🥔", "category": "Vegetables", "stock": 200},
        {"name": "Fresh Tomato",      "price": 9.00,  "description": "Ripe red tomatoes, 1kg.",         "image": "🍅", "category": "Vegetables", "stock": 150},
        {"name": "Fresh Onion",       "price": 10.00, "description": "Fresh onions, 1kg.",              "image": "🧅", "category": "Vegetables", "stock": 200},
        {"name": "Fresh Carrot",      "price": 12.00, "description": "Crunchy fresh carrots, 1kg.",     "image": "🥕", "category": "Vegetables", "stock": 120},
        {"name": "Fresh Mint Leaves", "price": 1.00,  "description": "Premium mint leaves bunch.",      "image": "🌿", "category": "Vegetables", "stock": 80},
        {"name": "Egg",               "price": 1.00,  "description": "Farm fresh eggs.",                "image": "🥚", "category": "Dairy",      "stock": 500},
    ]
    db.products.insert_many(sample)
    print(f"🌱 Seeded {len(sample)} sample products.")


def seed_admin():
    db     = get_db()
    email  = os.getenv("ADMIN_EMAIL",    "admin@freshmart.com")
    passwd = os.getenv("ADMIN_PASSWORD", "admin123")

    existing = db.users.find_one({"email": email})
    if existing:
        # Make sure the role is set to admin (fixes existing accounts)
        if existing.get("role") != "admin":
            db.users.update_one({"email": email}, {"$set": {"role": "admin"}})
            print(f"🔐 Updated existing user to admin: {email}")
        else:
            print(f"✅ Admin already exists: {email}")
        return

    from datetime import datetime
    pw_hash = bcrypt.hashpw(passwd.encode(), bcrypt.gensalt()).decode()
    db.users.insert_one({
        "name": "Admin", "email": email,
        "password_hash": pw_hash, "role": "admin",
        "primary_address": {}, "secondary_address": {},
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    })
    print(f"🔐 Admin created  →  email: {email}   password: {passwd}")


if __name__ == "__main__":
    connect_db()
    seed_products()
    seed_admin()
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🚀 Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)