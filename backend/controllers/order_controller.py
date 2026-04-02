from bson import ObjectId
from datetime import datetime
from config.db import get_db
from models.orders import Order
from models.cart import Cart
from controllers.cart_controller import clear_cart


def place_order(user_id: str, data: dict) -> tuple[dict, int]:
    db = get_db()

    cart_doc = db.carts.find_one({"user_id": user_id})
    items    = cart_doc.get("items", []) if cart_doc else []
    if not items:
        return {"error": "Your cart is empty."}, 400

    address = data.get("address") or {}

    # Accept both "zip" and "postal_code" for backwards compatibility
    if not address.get("zip") and address.get("postal_code"):
        address["zip"] = address["postal_code"]

    required_fields = ["full_name", "street", "city"]
    missing = [f for f in required_fields if not address.get(f, "").strip()]
    if missing:
        return {"error": f"Missing address fields: {', '.join(missing)}"}, 400

    total  = Cart.total(items)
    order  = Order(user_id=user_id, items=items, total=total, address=address)
    result = db.orders.insert_one(order.to_dict())

    clear_cart(user_id)

    inserted = db.orders.find_one({"_id": result.inserted_id})
    return {
        "message": "Order placed successfully! 🎉",
        "order":   Order.serialize(inserted),
    }, 201


def get_user_orders(user_id: str) -> tuple[dict, int]:
    db     = get_db()
    orders = [Order.serialize(o) for o in
              db.orders.find({"user_id": user_id}).sort("placed_at", -1)]
    return {"orders": orders, "count": len(orders)}, 200


def get_order(user_id: str, order_id: str) -> tuple[dict, int]:
    try:
        oid = ObjectId(order_id)
    except Exception:
        return {"error": "Invalid order ID."}, 400

    db    = get_db()
    order = db.orders.find_one({"_id": oid, "user_id": user_id})
    if not order:
        return {"error": "Order not found."}, 404
    return {"order": Order.serialize(order)}, 200


def cancel_order(user_id: str, order_id: str) -> tuple[dict, int]:
    try:
        oid = ObjectId(order_id)
    except Exception:
        return {"error": "Invalid order ID."}, 400

    db    = get_db()
    order = db.orders.find_one({"_id": oid, "user_id": user_id})
    if not order:
        return {"error": "Order not found."}, 404
    if order["status"] not in ("pending", "confirmed"):
        return {"error": f"Cannot cancel an order with status '{order['status']}'"}, 400

    db.orders.update_one({"_id": oid}, {"$set": {"status": "cancelled",
                                                   "updated_at": datetime.utcnow()}})
    updated = db.orders.find_one({"_id": oid})
    return {"message": "Order cancelled.", "order": Order.serialize(updated)}, 200