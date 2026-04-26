import os
import bcrypt
from datetime import datetime
from bson import ObjectId
from config.db import get_db


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_admin_emails() -> list[str]:
    """Return the current list of authorised admin emails from DB + .env."""
    db     = get_db()
    stored = [d["email"] for d in db.admin_emails.find({}, {"email": 1})]
    env    = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    return list(set(stored + env))


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ── Product Management ────────────────────────────────────────────────────────

def get_all_products() -> tuple[dict, int]:
    db       = get_db()
    products = [_serialize(p) for p in db.products.find()]
    return {"products": products, "count": len(products)}, 200


def create_product(data: dict) -> tuple[dict, int]:
    required = ["name", "price"]
    for f in required:
        if not data.get(f):
            return {"error": f"'{f}' is required."}, 400

    db  = get_db()
    doc = {
        "name":        data["name"].strip(),
        "price":       float(data["price"]),
        "description": data.get("description", ""),
        "image":       data.get("image", "📦"),
        "category":    data.get("category", "General"),
        "stock":       int(data.get("stock", 0)),
        "created_at":  datetime.utcnow(),
        "updated_at":  datetime.utcnow(),
    }
    result = db.products.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return {"message": "Product created.", "product": _serialize(doc)}, 201


def update_product(product_id: str, data: dict) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    updates = {k: v for k, v in {
        "name":        data.get("name"),
        "price":       float(data["price"]) if data.get("price") else None,
        "description": data.get("description"),
        "image":       data.get("image"),
        "category":    data.get("category"),
        "stock":       int(data["stock"]) if data.get("stock") is not None else None,
    }.items() if v is not None}

    if not updates:
        return {"error": "No fields to update."}, 400

    updates["updated_at"] = datetime.utcnow()
    db.products.update_one({"_id": oid}, {"$set": updates})
    product = db.products.find_one({"_id": oid})
    return {"message": "Product updated.", "product": _serialize(product)}, 200


def delete_product(product_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    result = db.products.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return {"error": "Product not found."}, 404
    return {"message": "Product deleted."}, 200


# ── User Management ───────────────────────────────────────────────────────────

def get_all_users() -> tuple[dict, int]:
    db    = get_db()
    users = []
    for u in db.users.find({}, {"password_hash": 0}):
        users.append(_serialize(u))
    return {"users": users, "count": len(users)}, 200


def delete_user(user_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return {"error": "Invalid user ID."}, 400

    user = db.users.find_one({"_id": oid})
    if not user:
        return {"error": "User not found."}, 404
    if user.get("role") == "admin":
        return {"error": "Cannot delete an admin account."}, 403

    db.users.delete_one({"_id": oid})
    return {"message": "User deleted."}, 200


def block_user(user_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return {"error": "Invalid user ID."}, 400

    user = db.users.find_one({"_id": oid})
    if not user:
        return {"error": "User not found."}, 404
    if user.get("role") == "admin":
        return {"error": "Cannot block an admin account."}, 403

    db.users.update_one({"_id": oid}, {"$set": {"blocked": True, "updated_at": datetime.utcnow()}})
    return {"message": "User blocked."}, 200


def unblock_user(user_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return {"error": "Invalid user ID."}, 400

    db.users.update_one({"_id": oid}, {"$set": {"blocked": False, "updated_at": datetime.utcnow()}})
    return {"message": "User unblocked."}, 200


# ── Order Management ──────────────────────────────────────────────────────────

def get_all_orders() -> tuple[dict, int]:
    db     = get_db()
    orders = [_serialize(o) for o in db.orders.find().sort("placed_at", -1)]
    return {"orders": orders, "count": len(orders)}, 200


# ── Admin Email Management ────────────────────────────────────────────────────

def get_admin_emails() -> tuple[dict, int]:
    return {"admin_emails": _get_admin_emails()}, 200


def add_admin_email(data: dict) -> tuple[dict, int]:
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", os.getenv("ADMIN_PASSWORD", "Admin@1234"))

    if not email:
        return {"error": "Email is required."}, 400

    db = get_db()
    if db.admin_emails.find_one({"email": email}):
        return {"error": "Email already an admin."}, 409

    # Add to admin_emails collection
    db.admin_emails.insert_one({"email": email, "added_at": datetime.utcnow()})

    # Create user account if doesn't exist
    if not db.users.find_one({"email": email}):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.users.insert_one({
            "name":              data.get("name", email.split("@")[0].capitalize()),
            "email":             email,
            "password_hash":     hashed,
            "role":              "admin",
            "phone":             data.get("phone", ""),
            "primary_address":   {},
            "secondary_address": {},
            "created_at":        datetime.utcnow(),
            "updated_at":        datetime.utcnow(),
        })
    else:
        # Promote existing user to admin
        db.users.update_one({"email": email}, {"$set": {"role": "admin", "updated_at": datetime.utcnow()}})

    return {"message": f"{email} added as admin."}, 201


def remove_admin_email(data: dict) -> tuple[dict, int]:
    email = (data.get("email") or "").strip().lower()
    if not email:
        return {"error": "Email is required."}, 400

    # Prevent removing env-seeded admins
    env_admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    if email in env_admins:
        return {"error": "Cannot remove an admin seeded from .env. Remove from ADMIN_EMAILS instead."}, 403

    db = get_db()
    db.admin_emails.delete_one({"email": email})
    db.users.update_one({"email": email}, {"$set": {"role": "user", "updated_at": datetime.utcnow()}})
    return {"message": f"{email} removed from admins."}, 200

def promote_to_vendor(user_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return {"error": "Invalid user ID."}, 400

    user = db.users.find_one({"_id": oid})
    if not user:
        return {"error": "User not found."}, 404
    if user.get("role") == "admin":
        return {"error": "Cannot change role of an admin account."}, 403
    if user.get("role") == "vendor":
        return {"error": "User is already a vendor."}, 409

    db.users.update_one({"_id": oid}, {"$set": {
        "role":         "vendor",
        "wants_vendor": False,
        "updated_at":   datetime.utcnow(),
    }})
    return {"message": "User promoted to vendor."}, 200