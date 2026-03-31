import jwt
from functools import wraps
from flask import request, jsonify, g
from bson import ObjectId
from config.db import get_db
from controllers.auth_controller import decode_token


# ── Shared internal helper ───────────────────────────────────────────────────

def _extract_user(required_role: str = None):
    """
    Decode token, load user from DB, optionally enforce a role.
    Returns (user_doc, error_response) — exactly one will be None.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None, (jsonify({"error": "Authorization token missing."}), 401)
    try:
        payload = decode_token(token)
        db      = get_db()
        user    = db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            return None, (jsonify({"error": "User not found."}), 404)
        if required_role and user.get("role") != required_role:
            return None, (jsonify({"error": f"{required_role.capitalize()} access required."}), 403)
        return user, None
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token expired. Please log in again."}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Invalid token."}), 401)


# ── Public decorators ────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = _extract_user()
        if err:
            return err
        g.user_id = str(user["_id"])
        g.user    = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Allows both admin (seller) and owner."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = _extract_user()
        if err:
            return err
        if user.get("role") not in ("admin", "owner"):
            return jsonify({"error": "Admin access required."}), 403
        g.user_id = str(user["_id"])
        g.user    = user
        return f(*args, **kwargs)
    return decorated


def require_owner(f):
    """Allows only the owner (super-admin)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = _extract_user(required_role="owner")
        if err:
            return err
        g.user_id = str(user["_id"])
        g.user    = user
        return f(*args, **kwargs)
    return decorated
