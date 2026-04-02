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
    name = (data.get("name") or "").strip()
    price = data.get("price")
    description = (data.get("description") or "").strip()

    if not name or price is None:
        return {"error": "Name and price are required."}, 400
    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except (ValueError, TypeError):
        return {"error": "Price must be a positive number."}, 400

    db = get_db()
    product = {"name": name, "price": price, "description": description}
    result = db.products.insert_one(product)
    inserted = db.products.find_one({"_id": result.inserted_id})
    return {"message": "Product created.", "product": _serialize(inserted)}, 201