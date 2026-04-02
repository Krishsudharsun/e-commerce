from datetime import datetime

class CartItem:
    def __init__(self, product_id: str, name: str, price: float,
                 quantity: int = 1, image: str = ""):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.quantity = quantity
        self.image = image

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "image": self.image,
        }

class Cart:
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

    @staticmethod
    def total(items: list) -> float:
        return round(sum(i["price"] * i["quantity"] for i in items), 2)