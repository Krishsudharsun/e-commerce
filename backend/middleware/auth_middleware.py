import os
import jwt
from functools import wraps
from flask import request, jsonify, g
from bson import ObjectId
from config.db import get_db

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return jsonify({"error": "Authorization token missing."}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            db = get_db()
            user = db.users.find_one({"_id": ObjectId(payload["sub"])})
            if not user:
                return jsonify({"error": "User not found."}), 404
            g.user_id = str(user["_id"])
            g.user = user
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired. Please log in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."}), 401
        return f(*args, **kwargs)
    return decorated