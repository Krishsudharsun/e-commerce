import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
from config.db import get_db
from models.user import User

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", 24))


# ── helpers ────────────────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def _generate_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def _decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


# ── public controllers ──────────────────────────────────────────────────────────

def register_user(data: dict) -> tuple[dict, int]:
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return {"error": "Name, email, and password are required."}, 400
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters."}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "An account with that email already exists."}, 409

    user = User(email=email, password_hash=_hash_password(password), name=name)
    result = db.users.insert_one(user.to_dict())
    inserted = db.users.find_one({"_id": result.inserted_id})

    token = _generate_token(str(result.inserted_id), email)
    return {
        "message": "Account created successfully.",
        "token": token,
        "user": User.from_dict(inserted),
    }, 201


def login_user(data: dict) -> tuple[dict, int]:
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return {"error": "Email and password are required."}, 400

    db = get_db()
    user_doc = db.users.find_one({"email": email})
    if not user_doc or not _verify_password(password, user_doc["password_hash"]):
        return {"error": "Invalid email or password."}, 401

    token = _generate_token(str(user_doc["_id"]), email)
    return {
        "message": "Login successful.",
        "token": token,
        "user": User.from_dict(user_doc),
    }, 200


def get_current_user(token: str) -> tuple[dict, int]:
    if not token:
        return {"error": "Authorization token missing."}, 401
    try:
        payload = _decode_token(token)
        db = get_db()
        user_doc = db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user_doc:
            return {"error": "User not found."}, 404
        return {"user": User.from_dict(user_doc)}, 200
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired. Please log in again."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401