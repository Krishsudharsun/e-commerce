from datetime import datetime
from bson import ObjectId
from config.db import get_db


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def get_all_products() -> tuple[dict, int]:
    db = get_db()
    products = [_serialize(p) for p in db.products.find()]
    return {"products": products, "count": len(products)}, 200


def get_product(product_id: str) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400
    db = get_db()
    doc = db.products.find_one({"_id": oid})
    if not doc:
        return {"error": "Product not found."}, 404
    return {"product": _serialize(doc)}, 200


def create_product(data: dict) -> tuple[dict, int]:
    name        = (data.get("name")        or "").strip()
    description = (data.get("description") or "").strip()
    category    = (data.get("category")    or "General").strip()
    image       = (data.get("image")       or "📦").strip()
    price       = data.get("price")
    stock       = data.get("stock", 0)

    if not name or price is None:
        return {"error": "Name and price are required."}, 400
    try:
        price = float(price)
        stock = int(stock)
        if price < 0 or stock < 0:
            raise ValueError
    except (ValueError, TypeError):
        return {"error": "Price and stock must be positive numbers."}, 400

    db = get_db()
    product = {
        "name": name, "price": price, "description": description,
        "category": category, "image": image, "stock": stock,
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    result   = db.products.insert_one(product)
    inserted = db.products.find_one({"_id": result.inserted_id})
    return {"message": "Product created.", "product": _serialize(inserted)}, 201


def update_product(product_id: str, data: dict) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    db = get_db()
    if not db.products.find_one({"_id": oid}):
        return {"error": "Product not found."}, 404

    updates = {"updated_at": datetime.utcnow()}
    if "name"        in data: updates["name"]        = str(data["name"]).strip()
    if "description" in data: updates["description"] = str(data["description"]).strip()
    if "category"    in data: updates["category"]    = str(data["category"]).strip()
    if "image"       in data: updates["image"]       = str(data["image"]).strip()
    if "price"       in data:
        try:
            updates["price"] = float(data["price"])
            if updates["price"] < 0: raise ValueError
        except (ValueError, TypeError):
            return {"error": "Price must be a positive number."}, 400
    if "stock" in data:
        try:
            updates["stock"] = int(data["stock"])
            if updates["stock"] < 0: raise ValueError
        except (ValueError, TypeError):
            return {"error": "Stock must be a positive integer."}, 400

    db.products.update_one({"_id": oid}, {"$set": updates})
    updated = db.products.find_one({"_id": oid})
    return {"message": "Product updated.", "product": _serialize(updated)}, 200


def delete_product(product_id: str) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    db = get_db()
    result = db.products.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return {"error": "Product not found."}, 404
    return {"message": "Product deleted."}, 200


# ── Admin helpers ───────────────────────────────────────────────────────────────

def admin_get_stats() -> tuple[dict, int]:
    db = get_db()
    total_products = db.products.count_documents({})
    total_users    = db.users.count_documents({})
    total_orders   = db.orders.count_documents({})
    revenue        = sum(
        o.get("total", 0)
        for o in db.orders.find({"status": {"$nin": ["cancelled"]}})
    )
    orders_by_status = {}
    for status in ["pending", "confirmed", "shipped", "delivered", "cancelled"]:
        orders_by_status[status] = db.orders.count_documents({"status": status})
    return {
        "total_products": total_products,
        "total_users":    total_users,
        "total_orders":   total_orders,
        "revenue":        round(revenue, 2),
        "orders_by_status": orders_by_status,
    }, 200


def admin_get_all_orders() -> tuple[dict, int]:
    from models.orders import Order
    db = get_db()
    orders = [Order.serialize(o) for o in db.orders.find().sort("placed_at", -1)]
    return {"orders": orders, "count": len(orders)}, 200


def admin_update_order_status(order_id: str, status: str) -> tuple[dict, int]:
    valid = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if status not in valid:
        return {"error": f"Status must be one of: {', '.join(valid)}"}, 400
    try:
        oid = ObjectId(order_id)
    except Exception:
        return {"error": "Invalid order ID."}, 400
    from models.orders import Order
    db = get_db()
    if not db.orders.find_one({"_id": oid}):
        return {"error": "Order not found."}, 404
    db.orders.update_one({"_id": oid}, {"$set": {"status": status, "updated_at": datetime.utcnow()}})
    updated = db.orders.find_one({"_id": oid})
    return {"message": "Order status updated.", "order": Order.serialize(updated)}, 200


def admin_get_all_users() -> tuple[dict, int]:
    from models.user import User
    db = get_db()
    users = [User.from_dict(u) for u in db.users.find()]
    return {"users": users, "count": len(users)}, 200