from datetime import datetime

ROLES = ("user", "admin")


class User:
    def __init__(self, email: str, password_hash: str, name: str,
                 role: str = "user",
                 phone: str = "",
                 primary_address: dict = None,
                 secondary_address: dict = None):
        self.name              = name
        self.email             = email
        self.password_hash     = password_hash
        self.role              = role if role in ROLES else "user"
        self.phone             = phone
        self.primary_address   = primary_address   or {}
        self.secondary_address = secondary_address or {}
        self.created_at        = datetime.utcnow()
        self.updated_at        = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "name":              self.name,
            "email":             self.email,
            "password_hash":     self.password_hash,
            "role":              self.role,
            "phone":             self.phone,
            "primary_address":   self.primary_address,
            "secondary_address": self.secondary_address,
            "created_at":        self.created_at,
            "updated_at":        self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        """Return a safe public representation (no password hash)."""
        created = data.get("created_at", "")
        return {
            "id":                str(data["_id"]),
            "name":              data.get("name",  ""),
            "email":             data.get("email", ""),
            "role":              data.get("role",  "user"),
            "phone":             data.get("phone", ""),
            "primary_address":   data.get("primary_address",   {}),
            "secondary_address": data.get("secondary_address", {}),
            "created_at":        created.isoformat() if isinstance(created, datetime) else str(created),
        }