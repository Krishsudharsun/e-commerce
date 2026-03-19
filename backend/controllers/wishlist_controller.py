from datetime import datetime
from bson import ObjectId
from config.db import get_db


def _get_wishlist(db, user_id: str) -> dict:
    return db.wishlists.find_one({"user_id": user_id}) or {"user_id": user_id, "items": []}


def get_wishlist(user_id: str) -> tuple[dict, int]:
    db = get_db()
    wl = _get_wishlist(db, user_id)
    return {"items": wl.get("items", []), "count": len(wl.get("items", []))}, 200


def toggle_wishlist(user_id: str, data: dict) -> tuple[dict, int]:
    product_id = (data.get("product_id") or "").strip()
    if not product_id:
        return {"error": "product_id is required."}, 400

    db = get_db()
<<<<<<< HEAD
=======

    # validate product exists
>>>>>>> 35e5bf13951267a5c7c5bb711e069538ab6ea9d9
    try:
        product = db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        return {"error": "Invalid product ID."}, 400
    if not product:
        return {"error": "Product not found."}, 404

    wl = _get_wishlist(db, user_id)
    items = wl.get("items", [])
    ids = [i["product_id"] for i in items]

    if product_id in ids:
<<<<<<< HEAD
        items = [i for i in items if i["product_id"] != product_id]
        action = "removed"
    else:
=======
        # remove from wishlist
        items = [i for i in items if i["product_id"] != product_id]
        action = "removed"
    else:
        # add to wishlist
>>>>>>> 35e5bf13951267a5c7c5bb711e069538ab6ea9d9
        items.append({
            "product_id": product_id,
            "name": product["name"],
            "price": product["price"],
            "image": product.get("image", ""),
            "category": product.get("category", ""),
            "description": product.get("description", ""),
        })
        action = "added"

    db.wishlists.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
<<<<<<< HEAD
    return {
        "message": f"Product {action} {'to' if action == 'added' else 'from'} wishlist.",
        "action": action,
        "items": items,
        "count": len(items)
    }, 200
=======
    return {"message": f"Product {action} {'to' if action == 'added' else 'from'} wishlist.",
            "action": action, "items": items, "count": len(items)}, 200
>>>>>>> 35e5bf13951267a5c7c5bb711e069538ab6ea9d9


def remove_from_wishlist(user_id: str, product_id: str) -> tuple[dict, int]:
    db = get_db()
    wl = _get_wishlist(db, user_id)
    items = [i for i in wl.get("items", []) if i["product_id"] != product_id]
    db.wishlists.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"message": "Removed from wishlist.", "items": items, "count": len(items)}, 200