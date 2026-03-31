"""
Admin controllers — scoped by role.
- owner: sees ALL data across all sellers
- admin: sees only their own products/orders
"""
from datetime import datetime
from bson import ObjectId
from config.db import get_db
from models.orders import Order
from models.user import User

VALID_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]


def admin_get_stats(caller_id: str, caller_role: str) -> tuple[dict, int]:
    db = get_db()

    # Scope products by owner if admin (not owner)
    product_query = {} if caller_role == "owner" else {"owner_id": caller_id}
    total_products = db.products.count_documents(product_query)

    # Scope orders: find order IDs that contain seller's products
    if caller_role == "owner":
        order_query = {}
    else:
        my_product_ids = [
            str(p["_id"]) for p in db.products.find({"owner_id": caller_id}, {"_id": 1})
        ]
        order_query = {"items.product_id": {"$in": my_product_ids}}

    total_orders = db.orders.count_documents(order_query)
    total_users  = db.users.count_documents({}) if caller_role == "owner" else None

    revenue = sum(
        o.get("total", 0)
        for o in db.orders.find({**order_query, "status": {"$nin": ["cancelled"]}})
    )
    orders_by_status = {
        s: db.orders.count_documents({**order_query, "status": s}) for s in VALID_STATUSES
    }

    result = {
        "total_products":   total_products,
        "total_orders":     total_orders,
        "revenue":          round(revenue, 2),
        "orders_by_status": orders_by_status,
    }
    if caller_role == "owner":
        result["total_users"] = total_users

    return result, 200


def admin_get_all_orders(caller_id: str, caller_role: str) -> tuple[dict, int]:
    db = get_db()
    if caller_role == "owner":
        query = {}
    else:
        my_product_ids = [
            str(p["_id"]) for p in db.products.find({"owner_id": caller_id}, {"_id": 1})
        ]
        query = {"items.product_id": {"$in": my_product_ids}}

    orders = [Order.serialize(o) for o in db.orders.find(query).sort("placed_at", -1)]
    return {"orders": orders, "count": len(orders)}, 200


def admin_update_order_status(order_id: str, status: str,
                               caller_id: str, caller_role: str) -> tuple[dict, int]:
    if status not in VALID_STATUSES:
        return {"error": f"Status must be one of: {', '.join(VALID_STATUSES)}"}, 400
    try:
        oid = ObjectId(order_id)
    except Exception:
        return {"error": "Invalid order ID."}, 400

    db    = get_db()
    order = db.orders.find_one({"_id": oid})
    if not order:
        return {"error": "Order not found."}, 404

    # Admins can only update orders that contain their products
    if caller_role != "owner":
        my_product_ids = [
            str(p["_id"]) for p in db.products.find({"owner_id": caller_id}, {"_id": 1})
        ]
        order_pids = [i.get("product_id") for i in order.get("items", [])]
        if not any(pid in my_product_ids for pid in order_pids):
            return {"error": "You do not have permission to update this order."}, 403

    db.orders.update_one(
        {"_id": oid},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )
    updated = db.orders.find_one({"_id": oid})
    return {"message": "Order status updated.", "order": Order.serialize(updated)}, 200


def admin_get_all_users() -> tuple[dict, int]:
    """Owner only."""
    db    = get_db()
    users = [User.from_dict(u) for u in db.users.find()]
    return {"users": users, "count": len(users)}, 200
