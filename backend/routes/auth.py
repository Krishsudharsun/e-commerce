from flask import Blueprint, request, jsonify
from controllers.auth_controller import register_user, login_user, get_current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    return jsonify(*register_user(request.get_json(silent=True) or {}))

@auth_bp.route("/login", methods=["POST"])
def login():
    return jsonify(*login_user(request.get_json(silent=True) or {}))

@auth_bp.route("/me", methods=["GET"])
def me():
    token = (request.headers.get("Authorization", "")).removeprefix("Bearer ").strip()
    return jsonify(*get_current_user(token))
