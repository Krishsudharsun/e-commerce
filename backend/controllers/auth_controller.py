import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
from config.db import get_db
from models.user import User
from controllers.otp_controller import _normalize_phone

SECRET_KEY         = os.getenv("JWT_SECRET", "change-this-in-production")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", 24))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
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

def _decode_token(token: str) -> dict:
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


def register_user(data: dict) -> tuple[dict, int]:
    name     = (data.get("name")     or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""
    phone    = (data.get("phone")    or "").strip()

    if not name or not email or not password:
        return {"error": "Name, email, and password are required."}, 400
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters."}, 400

    if phone:
        phone = _normalize_phone(phone)
        db = get_db()
        otp_record = db.otps.find_one({"phone": phone, "used": True}, sort=[("created_at", -1)])
        if not otp_record:
            return {"error": "Phone number not verified. Please verify your OTP first."}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "An account with that email already exists."}, 409
    if phone and db.users.find_one({"phone": phone}):
        return {"error": "An account with that phone number already exists."}, 409

    primary   = _parse_address(data, "primary_")
    secondary = _parse_address(data, "secondary_")
    if not any(secondary.values()):
        secondary = {}

    user   = User(email=email, password_hash=_hash_password(password),
                  name=name, role="user", phone=phone,
                  primary_address=primary, secondary_address=secondary)
    result   = db.users.insert_one(user.to_dict())
    inserted = db.users.find_one({"_id": result.inserted_id})

    token = _generate_token(str(result.inserted_id), email, role="user")
    return {"message": "Account created successfully.", "token": token,
            "user": User.from_dict(inserted)}, 201


def login_user(data: dict) -> tuple[dict, int]:
    email        = (data.get("email")    or "").strip().lower()
    password     =  data.get("password") or ""
    phone        = (data.get("phone")    or "").strip()
    otp_verified =  data.get("otp_verified", False)

    db = get_db()

    # Branch 1: Phone OTP login
    if phone and otp_verified:
        phone  = _normalize_phone(phone)
        cutoff = datetime.utcnow() - timedelta(minutes=15)
        record = db.otps.find_one(
            {"phone": phone, "used": True, "created_at": {"$gte": cutoff}},
            sort=[("created_at", -1)]
        )
        if not record:
            return {"error": "Phone OTP not verified or has expired."}, 401
        user_doc = db.users.find_one({"phone": phone})
        if not user_doc:
            return {"error": "No account found for this phone number."}, 404
        token = _generate_token(str(user_doc["_id"]),
                                user_doc.get("email", ""),
                                user_doc.get("role", "user"))
        return {"message": "Login successful.", "token": token,
                "user": User.from_dict(user_doc)}, 200

    # Branch 2: Email OTP login
    if email and otp_verified:
        cutoff = datetime.utcnow() - timedelta(minutes=15)
        record = db.otps.find_one(
            {"email": email, "used": True, "created_at": {"$gte": cutoff}},
            sort=[("created_at", -1)]
        )
        if not record:
            return {"error": "Email OTP not verified or has expired."}, 401
        user_doc = db.users.find_one({"email": email})
        if not user_doc:
            return {"error": "No account found for this email."}, 404
        token = _generate_token(str(user_doc["_id"]), email,
                                user_doc.get("role", "user"))
        return {"message": "Login successful.", "token": token,
                "user": User.from_dict(user_doc)}, 200

    # Branch 3: Email + password login (admin and legacy)
    if not email or not password:
        return {"error": "Email and password are required."}, 400
    user_doc = db.users.find_one({"email": email})
    if not user_doc or not _verify_password(password, user_doc.get("password_hash", "")):
        return {"error": "Invalid email or password."}, 401
    token = _generate_token(str(user_doc["_id"]), email,
                            user_doc.get("role", "user"))
    return {"message": "Login successful.", "token": token,
            "user": User.from_dict(user_doc)}, 200


def get_current_user(token: str) -> tuple[dict, int]:
    if not token:
        return {"error": "Authorization token missing."}, 401
    try:
        payload  = _decode_token(token)
        db       = get_db()
        user_doc = db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user_doc:
            return {"error": "User not found."}, 404
        return {"user": User.from_dict(user_doc)}, 200
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired. Please log in again."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401
