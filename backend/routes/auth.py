from flask import Blueprint, request, jsonify
from controllers.auth_controller  import register_user, login_user, get_current_user
from controllers.otp_controller   import send_otp, verify_otp

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
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    response, status = get_current_user(token)
    return jsonify(response), status


@auth_bp.route("/otp/send", methods=["POST"])
def otp_send():
    data = request.get_json(silent=True) or {}
    response, status = send_otp(data)
    return jsonify(response), status


@auth_bp.route("/otp/verify", methods=["POST"])
def otp_verify():
    data = request.get_json(silent=True) or {}
    response, status = verify_otp(data)
    return jsonify(response), status
