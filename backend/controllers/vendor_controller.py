import os
import bcrypt
from datetime import datetime
from bson import ObjectId
from config.db import get_db


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ── Products (vendor-scoped) ───────────────────────────────────────────────────

def vendor_get_products(vendor_id: str) -> tuple[dict, int]:
    db = get_db()
    products = [_serialize(p) for p in db.products.find({"vendor_id": vendor_id})]
    return {"products": products, "count": len(products)}, 200


def vendor_create_product(vendor_id: str, data: dict) -> tuple[dict, int]:
    if not data.get("name") or not data.get("price"):
        return {"error": "'name' and 'price' are required."}, 400

    db = get_db()
    doc = {
        "vendor_id":   vendor_id,
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
    inserted = db.products.find_one({"_id": result.inserted_id})
    return {"message": "Product created.", "product": _serialize(inserted)}, 201


def vendor_update_product(vendor_id: str, product_id: str, data: dict) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    product = db.products.find_one({"_id": oid})
    if not product:
        return {"error": "Product not found."}, 404
    if product.get("vendor_id") != vendor_id:
        return {"error": "You do not own this product."}, 403

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
    updated = db.products.find_one({"_id": oid})
    return {"message": "Product updated.", "product": _serialize(updated)}, 200


def vendor_delete_product(vendor_id: str, product_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    product = db.products.find_one({"_id": oid})
    if not product:
        return {"error": "Product not found."}, 404
    if product.get("vendor_id") != vendor_id:
        return {"error": "You do not own this product."}, 403

    db.products.delete_one({"_id": oid})
    return {"message": "Product deleted."}, 200


# ── Orders (vendor-scoped) ─────────────────────────────────────────────────────
# An order is "visible" to a vendor if at least one item in the order
# belongs to a product owned by that vendor.

def vendor_get_orders(vendor_id: str) -> tuple[dict, int]:
    db = get_db()

    # Get all product IDs owned by this vendor
    vendor_product_ids = {
        str(p["_id"])
        for p in db.products.find({"vendor_id": vendor_id}, {"_id": 1})
    }

    if not vendor_product_ids:
        return {"orders": [], "count": 0}, 200

    # Pull every order; keep only those that contain ≥1 vendor product
    # and strip each order down to only that vendor's items.
    visible_orders = []
    for order in db.orders.find().sort("placed_at", -1):
        items = order.get("items", [])
        vendor_items = [
            item for item in items
            if str(item.get("product_id", item.get("_id", ""))) in vendor_product_ids
        ]
        if not vendor_items:
            continue

        vendor_total = sum(
            float(i.get("price", 0)) * int(i.get("quantity", 1))
            for i in vendor_items
        )

        doc = _serialize(order)
        doc["items"]        = vendor_items          # only this vendor's items
        doc["vendor_total"] = round(vendor_total, 2)
        doc["full_item_count"] = len(items)         # total items in the whole order
        visible_orders.append(doc)

    return {"orders": visible_orders, "count": len(visible_orders)}, 200


# ── Vendor profile ─────────────────────────────────────────────────────────────

def vendor_get_profile(vendor_id: str) -> tuple[dict, int]:
    db = get_db()
    try:
        user = db.users.find_one({"_id": ObjectId(vendor_id)}, {"password_hash": 0})
    except Exception:
        return {"error": "Invalid vendor ID."}, 400
    if not user:
        return {"error": "Vendor not found."}, 404

    user["_id"] = str(user["_id"])
    for k, v in user.items():
        if isinstance(v, datetime):
            user[k] = v.isoformat()
    return {"vendor": user}, 200