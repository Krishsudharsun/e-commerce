from flask import Blueprint, request, jsonify
from controllers.auth_controller import register_user, login_user, get_current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    response, status = register_user(data)
    return jsonify(response), status


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    response, status = login_user(data)
    return jsonify(response), status


@auth_bp.route("/me", methods=["GET"])
def me():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    response, status = get_current_user(token)
    return jsonify(response), status