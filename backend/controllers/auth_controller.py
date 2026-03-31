import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
from config.db import get_db
from models.user import User

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY         = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", 24))


# ── Private helpers ──────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _generate_token(user_id: str, email: str, role: str = "user") -> str:
    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        "iat":   datetime.utcnow(),
        "exp":   datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Public — used by middleware too."""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def _parse_address(data: dict, prefix: str) -> dict:
    return {
        "full_name":   (data.get(f"{prefix}full_name")   or "").strip(),
        "street":      (data.get(f"{prefix}street")      or "").strip(),
        "area":        (data.get(f"{prefix}area")        or "").strip(),
        "city":        (data.get(f"{prefix}city")        or "").strip(),
        "postal_code": (data.get(f"{prefix}postal_code") or "").strip(),
        "state":       (data.get(f"{prefix}state")       or "").strip(),
        "country":     (data.get(f"{prefix}country")     or "India").strip(),
        "phone":       (data.get(f"{prefix}phone")       or "").strip(),
    }


# ── Public controllers ───────────────────────────────────────────────────────

def register_user(data: dict) -> tuple[dict, int]:
    name     = (data.get("name")     or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""

    if not name or not email or not password:
        return {"error": "Name, email, and password are required."}, 400
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters."}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "An account with that email already exists."}, 409

    primary   = _parse_address(data, "primary_")
    secondary = _parse_address(data, "secondary_")
    if not any(secondary.values()):
        secondary = {}

    user = User(
        email=email,
        password_hash=_hash_password(password),
        name=name,
        primary_address=primary,
        secondary_address=secondary,
    )
    result   = db.users.insert_one(user.to_dict())
    inserted = db.users.find_one({"_id": result.inserted_id})
    role     = inserted.get("role", "user")

    token = _generate_token(str(result.inserted_id), email, role)
    return {
        "message": "Account created successfully.",
        "token":   token,
        "user":    User.from_dict(inserted),
    }, 201


def login_user(data: dict) -> tuple[dict, int]:
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""

    if not email or not password:
        return {"error": "Email and password are required."}, 400

    db       = get_db()
    user_doc = db.users.find_one({"email": email})
    if not user_doc or not _verify_password(password, user_doc["password_hash"]):
        return {"error": "Invalid email or password."}, 401

    role  = user_doc.get("role", "user")
    token = _generate_token(str(user_doc["_id"]), email, role)
    return {
        "message": "Login successful.",
        "token":   token,
        "user":    User.from_dict(user_doc),
    }, 200


def get_current_user(token: str) -> tuple[dict, int]:
    if not token:
        return {"error": "Authorization token missing."}, 401
    try:
        payload  = decode_token(token)
        db       = get_db()
        user_doc = db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user_doc:
            return {"error": "User not found."}, 404
        return {"user": User.from_dict(user_doc)}, 200
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired. Please log in again."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401
