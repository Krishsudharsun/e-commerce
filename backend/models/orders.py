from datetime import datetime

ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]

class Order:
    def __init__(self, user_id: str, items: list,
                 total: float, address: dict = None):
        self.user_id = user_id
        self.items = items
        self.total = total
        self.status = "pending"
        self.address = address or {}
        self.placed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "items": self.items,
            "total": self.total,
            "status": self.status,
            "address": self.address,
            "placed_at": self.placed_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def serialize(doc: dict) -> dict:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        if "placed_at" in doc and hasattr(doc["placed_at"], "isoformat"):
            doc["placed_at"] = doc["placed_at"].isoformat()
        if "updated_at" in doc and hasattr(doc["updated_at"], "isoformat"):
            doc["updated_at"] = doc["updated_at"].isoformat()
        return doc
