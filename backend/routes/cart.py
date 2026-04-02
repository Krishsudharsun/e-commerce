from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth
from controllers.cart_controller import (
    get_cart, add_to_cart, update_cart_item,
    remove_from_cart, clear_cart,
)

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

@cart_bp.route("/", methods=["GET"])
@require_auth
def view_cart():
    response, status = get_cart(g.user_id)
    return jsonify(response), status

@cart_bp.route("/", methods=["POST"])
@require_auth
def add_item():
    data = request.get_json(silent=True) or {}
    response, status = add_to_cart(g.user_id, data)
    return jsonify(response), status

@cart_bp.route("/<product_id>", methods=["PUT"])
@require_auth
def update_item(product_id: str):
    data = request.get_json(silent=True) or {}
    response, status = update_cart_item(g.user_id, product_id, data)
    return jsonify(response), status

@cart_bp.route("/<product_id>", methods=["DELETE"])
@require_auth
def remove_item(product_id: str):
    response, status = remove_from_cart(g.user_id, product_id)
    return jsonify(response), status

@cart_bp.route("/", methods=["DELETE"])
@require_auth
def clear():
    response, status = clear_cart(g.user_id)
    return jsonify(response), status