from datetime import datetime
from bson import ObjectId

class User:
    def __init__(self, email: str, password_hash: str, name: str):
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        """Return a safe public version (no password)."""
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "created_at": data.get("created_at", "").isoformat()
            if isinstance(data.get("created_at"), datetime)
            else str(data.get("created_at", "")),
        }