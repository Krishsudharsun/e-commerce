from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth
from controllers.wishlist_controller import get_wishlist, toggle_wishlist, remove_from_wishlist

wishlist_bp = Blueprint("wishlist", __name__, url_prefix="/api/wishlist")

@wishlist_bp.route("/", methods=["GET"])
@require_auth
def view_wishlist():
    return jsonify(*get_wishlist(g.user_id))

@wishlist_bp.route("/", methods=["POST"])
@require_auth
def toggle():
    return jsonify(*toggle_wishlist(g.user_id, request.get_json(silent=True) or {}))

@wishlist_bp.route("/<product_id>", methods=["DELETE"])
@require_auth
def remove(product_id):
    return jsonify(*remove_from_wishlist(g.user_id, product_id))
