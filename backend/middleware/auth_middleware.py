import os
import jwt
from functools import wraps
from flask import request, jsonify, g
from bson import ObjectId
from config.db import get_db

SECRET_KEY = os.getenv("JWT_SECRET", "change-this-in-production")


def _extract_token() -> str:
    return request.headers.get("Authorization", "").removeprefix("Bearer ").strip()


def require_auth(f):
    """Rejects requests with no valid JWT. Sets g.user_id, g.user, g.role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Authorization token missing."}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            db   = get_db()
            user = db.users.find_one({"_id": ObjectId(payload["sub"])})
            if not user:
                return jsonify({"error": "User not found."}), 404
            g.user_id = str(user["_id"])
            g.user    = user
            g.role    = user.get("role", "user")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired. Please log in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """Only allows users whose role is in the given list.
    Usage: @require_role("admin")  or  @require_role("admin", "manager")
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.role not in roles:
                return jsonify({
                    "error": f"Access denied. Required role: {', '.join(roles)}."
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
