from datetime import datetime

ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]

class Order:
    def __init__(self, user_id, items, total, address=None):
        self.user_id = user_id
        self.items = items
        self.total = total
        self.status = "pending"
        self.address = address or {}
        self.placed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {"user_id": self.user_id, "items": self.items, "total": self.total,
                "status": self.status, "address": self.address,
                "placed_at": self.placed_at, "updated_at": self.updated_at}

    @staticmethod
    def serialize(doc):
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        for field in ("placed_at", "updated_at"):
            if field in doc and hasattr(doc[field], "isoformat"):
                doc[field] = doc[field].isoformat()
        return doc
