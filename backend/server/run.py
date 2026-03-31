import sys
import os
import bcrypt
import atexit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from config.db import connect_db, get_db, close_db
from routes.auth     import auth_bp
from routes.products import products_bp, admin_bp
from routes.cart     import cart_bp
from routes.orders   import orders_bp
from routes.wishlist import wishlist_bp
from routes.owner   import owner_bp

app = Flask(__name__)
CORS(
    app,
    origins=["http://localhost:3000", "http://127.0.0.1:3000",
             "http://localhost:5500", "http://127.0.0.1:5500", "null", "*"],
    supports_credentials=True,
)

# Register all blueprints
for bp in (auth_bp, products_bp, admin_bp, cart_bp, orders_bp, wishlist_bp, owner_bp):
    app.register_blueprint(bp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "E-Commerce API running 🚀"}, 200


# ── Seeding ──────────────────────────────────────────────────────────────────

def seed_products():
    db = get_db()
    if db.products.count_documents({}) > 0:
        return
    from datetime import datetime
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
    now = __import__("datetime").datetime.utcnow()
    for p in sample:
        p["created_at"] = now
        p["updated_at"] = now
    db.products.insert_many(sample)
    print(f"🌱 Seeded {len(sample)} sample products.")


def seed_owner():
    """Seeds the one true owner (super-admin) account on first run."""
    db     = get_db()
    email  = os.getenv("OWNER_EMAIL",    "owner@freshmart.com")
    passwd = os.getenv("OWNER_PASSWORD", "owner123")

    existing = db.users.find_one({"email": email})
    if existing:
        if existing.get("role") != "owner":
            db.users.update_one({"email": email}, {"$set": {"role": "owner"}})
            print(f"👑 Updated existing user to owner: {email}")
        else:
            print(f"✅ Owner already exists: {email}")
        return

    from datetime import datetime
    pw_hash = bcrypt.hashpw(passwd.encode(), bcrypt.gensalt()).decode()
    db.users.insert_one({
        "name": "Owner", "email": email,
        "password_hash": pw_hash, "role": "owner",
        "primary_address": {}, "secondary_address": {},
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    })
    print(f"👑 Owner created  →  email: {email}   password: {passwd}")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    connect_db()
    seed_products()
    seed_owner()
    atexit.register(close_db)   # Graceful shutdown

    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🚀 Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
