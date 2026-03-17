from datetime import datetime


class Wishlist:
    def __init__(self, user_id: str, items: list = None):
        self.user_id = user_id
        self.items = items or []
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "items": self.items,
            "updated_at": self.updated_at,
        }