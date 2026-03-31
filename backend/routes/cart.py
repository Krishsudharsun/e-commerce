from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth
from controllers.cart_controller import get_cart, add_to_cart, update_cart_item, remove_from_cart, clear_cart

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

@cart_bp.route("/", methods=["GET"])
@require_auth
def view_cart():
    return jsonify(*get_cart(g.user_id))

@cart_bp.route("/", methods=["POST"])
@require_auth
def add_item():
    return jsonify(*add_to_cart(g.user_id, request.get_json(silent=True) or {}))

@cart_bp.route("/<product_id>", methods=["PUT"])
@require_auth
def update_item(product_id):
    return jsonify(*update_cart_item(g.user_id, product_id, request.get_json(silent=True) or {}))

@cart_bp.route("/<product_id>", methods=["DELETE"])
@require_auth
def remove_item(product_id):
    return jsonify(*remove_from_cart(g.user_id, product_id))

@cart_bp.route("/", methods=["DELETE"])
@require_auth
def clear():
    return jsonify(*clear_cart(g.user_id))
