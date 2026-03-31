from datetime import datetime
from bson import ObjectId
from config.db import get_db
from models.cart import Cart


def _get_cart_doc(db, user_id: str) -> dict:
    return db.carts.find_one({"user_id": user_id}) or {"user_id": user_id, "items": []}


def _save_cart(db, user_id: str, items: list) -> None:
    db.carts.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def get_cart(user_id: str) -> tuple[dict, int]:
    db    = get_db()
    cart  = _get_cart_doc(db, user_id)
    items = cart.get("items", [])
    return {"items": items, "total": Cart.total(items), "count": len(items)}, 200


def add_to_cart(user_id: str, data: dict) -> tuple[dict, int]:
    product_id = (data.get("product_id") or "").strip()
    quantity   = int(data.get("quantity", 1))

    if not product_id:
        return {"error": "product_id is required."}, 400
    if quantity < 1:
        return {"error": "Quantity must be at least 1."}, 400

    db = get_db()
    try:
        product = db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        return {"error": "Invalid product ID."}, 400
    if not product:
        return {"error": "Product not found."}, 404

    # Stock validation
    available_stock = product.get("stock", 0)
    if available_stock < quantity:
        return {"error": f"Only {available_stock} unit(s) available in stock."}, 400

    cart  = _get_cart_doc(db, user_id)
    items = cart.get("items", [])

    for item in items:
        if item["product_id"] == product_id:
            new_qty = item["quantity"] + quantity
            if new_qty > available_stock:
                return {"error": f"Cannot add more — only {available_stock} unit(s) in stock."}, 400
            item["quantity"] = new_qty
            break
    else:
        items.append({
            "product_id": product_id,
            "name":       product["name"],
            "price":      product["price"],
            "quantity":   quantity,
            "image":      product.get("image", ""),
        })

    _save_cart(db, user_id, items)
    return {"message": "Item added to cart.", "items": items, "total": Cart.total(items)}, 200


def update_cart_item(user_id: str, product_id: str, data: dict) -> tuple[dict, int]:
    quantity = int(data.get("quantity", 1))
    if quantity < 0:
        return {"error": "Quantity cannot be negative."}, 400

    db    = get_db()
    cart  = _get_cart_doc(db, user_id)
    items = cart.get("items", [])

    if quantity == 0:
        items = [i for i in items if i["product_id"] != product_id]
    else:
        found = False
        for item in items:
            if item["product_id"] == product_id:
                # Stock check
                try:
                    product = db.products.find_one({"_id": ObjectId(product_id)})
                    if product and quantity > product.get("stock", 0):
                        return {"error": f"Only {product['stock']} unit(s) available."}, 400
                except Exception:
                    pass
                item["quantity"] = quantity
                found = True
                break
        if not found:
            return {"error": "Item not in cart."}, 404

    _save_cart(db, user_id, items)
    return {"message": "Cart updated.", "items": items, "total": Cart.total(items)}, 200


def remove_from_cart(user_id: str, product_id: str) -> tuple[dict, int]:
    db    = get_db()
    cart  = _get_cart_doc(db, user_id)
    items = [i for i in cart.get("items", []) if i["product_id"] != product_id]
    _save_cart(db, user_id, items)
    return {"message": "Item removed.", "items": items, "total": Cart.total(items)}, 200


def clear_cart(user_id: str) -> tuple[dict, int]:
    db = get_db()
    _save_cart(db, user_id, [])
    return {"message": "Cart cleared."}, 200
