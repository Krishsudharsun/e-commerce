from datetime import datetime
from bson import ObjectId
from config.db import get_db


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def get_all_products(category: str = None, search: str = None, owner_id: str = None) -> tuple[dict, int]:
    db    = get_db()
    query = {}
    if category:
        query["category"] = category
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if owner_id:                          # admin sees only their own products
        query["owner_id"] = owner_id
    products = [_serialize(p) for p in db.products.find(query)]
    return {"products": products, "count": len(products)}, 200


def get_product(product_id: str) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400
    db  = get_db()
    doc = db.products.find_one({"_id": oid})
    if not doc:
        return {"error": "Product not found."}, 404
    return {"product": _serialize(doc)}, 200


def create_product(data: dict, owner_id: str = None) -> tuple[dict, int]:
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

    db      = get_db()
    product = {
        "name": name, "price": price, "description": description,
        "category": category, "image": image, "stock": stock,
        "owner_id": owner_id,             # track which seller owns this product
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    result   = db.products.insert_one(product)
    inserted = db.products.find_one({"_id": result.inserted_id})
    return {"message": "Product created.", "product": _serialize(inserted)}, 201


def update_product(product_id: str, data: dict, owner_id: str = None) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    db      = get_db()
    product = db.products.find_one({"_id": oid})
    if not product:
        return {"error": "Product not found."}, 404
    # Admins can only edit their own products; owner can edit all
    if owner_id and product.get("owner_id") != owner_id:
        return {"error": "You do not have permission to edit this product."}, 403

    updates = {"updated_at": datetime.utcnow()}
    for field in ("name", "description", "category", "image"):
        if field in data:
            updates[field] = str(data[field]).strip()
    if "price" in data:
        try:
            updates["price"] = float(data["price"])
            if updates["price"] < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {"error": "Price must be a positive number."}, 400
    if "stock" in data:
        try:
            updates["stock"] = int(data["stock"])
            if updates["stock"] < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {"error": "Stock must be a positive integer."}, 400

    db.products.update_one({"_id": oid}, {"$set": updates})
    updated = db.products.find_one({"_id": oid})
    return {"message": "Product updated.", "product": _serialize(updated)}, 200


def delete_product(product_id: str, owner_id: str = None) -> tuple[dict, int]:
    try:
        oid = ObjectId(product_id)
    except Exception:
        return {"error": "Invalid product ID."}, 400

    db      = get_db()
    product = db.products.find_one({"_id": oid})
    if not product:
        return {"error": "Product not found."}, 404
    # Admins can only delete their own products; owner can delete all
    if owner_id and product.get("owner_id") != owner_id:
        return {"error": "You do not have permission to delete this product."}, 403
    db.products.delete_one({"_id": oid})
    return {"message": "Product deleted."}, 200
