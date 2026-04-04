from datetime import datetime


PAYMENT_STATUSES = ("payment_pending", "confirmed", "payment_failed",
                    "refund_initiated", "refunded")


class Payment:
    """Lightweight serializer for payment-related order fields."""

    @staticmethod
    def serialize(order_doc: dict) -> dict:
        doc = dict(order_doc)
        doc["id"] = str(doc.pop("_id"))
        for field in ("placed_at", "updated_at"):
            if field in doc and hasattr(doc[field], "isoformat"):
                doc[field] = doc[field].isoformat()
        return doc
