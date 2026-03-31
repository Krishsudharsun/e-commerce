from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_owner
from controllers.owner_controller import (
    create_seller, list_sellers, delete_seller, update_seller,
)

owner_bp = Blueprint("owner", __name__, url_prefix="/api/owner")


@owner_bp.route("/sellers", methods=["GET"])
@require_owner
def get_sellers():
    return jsonify(*list_sellers())


@owner_bp.route("/sellers", methods=["POST"])
@require_owner
def add_seller():
    data = request.get_json(silent=True) or {}
    return jsonify(*create_seller(data))


@owner_bp.route("/sellers/<seller_id>", methods=["PUT"])
@require_owner
def edit_seller(seller_id):
    data = request.get_json(silent=True) or {}
    return jsonify(*update_seller(seller_id, data))


@owner_bp.route("/sellers/<seller_id>", methods=["DELETE"])
@require_owner
def remove_seller(seller_id):
    return jsonify(*delete_seller(seller_id))
