"""
Owner-only controller — manage seller (admin) accounts.
Only users with role=owner can call these.
"""
import os
import bcrypt
from datetime import datetime
from bson import ObjectId
from config.db import get_db
from models.user import User


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_seller(data: dict) -> tuple[dict, int]:
    """Owner creates a new seller account with role=admin."""
    name     = (data.get("name")     or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""
    shop     = (data.get("shop_name") or "").strip()

    if not name or not email or not password:
        return {"error": "Name, email, and password are required."}, 400
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters."}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "An account with that email already exists."}, 409

    now = datetime.utcnow()
    seller = {
        "name":              name,
        "email":             email,
        "password_hash":     _hash_password(password),
        "role":              "admin",
        "shop_name":         shop or name,
        "primary_address":   {},
        "secondary_address": {},
        "created_at":        now,
        "updated_at":        now,
    }
    result   = db.users.insert_one(seller)
    inserted = db.users.find_one({"_id": result.inserted_id})
    return {
        "message": f"Seller account created for {name}.",
        "seller":  User.from_dict(inserted),
    }, 201


def list_sellers() -> tuple[dict, int]:
    """Return all users with role=admin (sellers)."""
    db      = get_db()
    sellers = [User.from_dict(u) for u in db.users.find({"role": "admin"})]
    return {"sellers": sellers, "count": len(sellers)}, 200


def delete_seller(seller_id: str) -> tuple[dict, int]:
    """Owner deletes a seller account (and optionally re-assigns their products)."""
    try:
        oid = ObjectId(seller_id)
    except Exception:
        return {"error": "Invalid seller ID."}, 400

    db     = get_db()
    seller = db.users.find_one({"_id": oid})
    if not seller:
        return {"error": "Seller not found."}, 404
    if seller.get("role") == "owner":
        return {"error": "Cannot delete the owner account."}, 403

    # Un-assign their products (set owner_id to None so they become unowned)
    db.products.update_many({"owner_id": seller_id}, {"$set": {"owner_id": None}})
    db.users.delete_one({"_id": oid})
    return {"message": f"Seller '{seller.get('name')}' deleted. Their products are now unassigned."}, 200


def update_seller(seller_id: str, data: dict) -> tuple[dict, int]:
    """Owner can reset a seller's name, shop name, or password."""
    try:
        oid = ObjectId(seller_id)
    except Exception:
        return {"error": "Invalid seller ID."}, 400

    db     = get_db()
    seller = db.users.find_one({"_id": oid, "role": "admin"})
    if not seller:
        return {"error": "Seller not found."}, 404

    updates = {"updated_at": datetime.utcnow()}
    if "name"      in data: updates["name"]      = str(data["name"]).strip()
    if "shop_name" in data: updates["shop_name"] = str(data["shop_name"]).strip()
    if "password"  in data:
        pw = data["password"]
        if len(pw) < 6:
            return {"error": "Password must be at least 6 characters."}, 400
        updates["password_hash"] = _hash_password(pw)

    db.users.update_one({"_id": oid}, {"$set": updates})
    updated = db.users.find_one({"_id": oid})
    return {"message": "Seller updated.", "seller": User.from_dict(updated)}, 200
