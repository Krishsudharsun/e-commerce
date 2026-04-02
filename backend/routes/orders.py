from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth
from controllers.order_controller import (
    place_order, get_user_orders, get_order, cancel_order,
)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

@orders_bp.route("/", methods=["POST"])
@require_auth
def create_order():
    data = request.get_json(silent=True) or {}
    response, status = place_order(g.user_id, data)
    return jsonify(response), status

@orders_bp.route("/", methods=["GET"])
@require_auth
def list_orders():
    response, status = get_user_orders(g.user_id)
    return jsonify(response), status

@orders_bp.route("/<order_id>", methods=["GET"])
@require_auth
def single_order(order_id: str):
    response, status = get_order(g.user_id, order_id)
    return jsonify(response), status

@orders_bp.route("/<order_id>/cancel", methods=["PATCH"])
@require_auth
def cancel(order_id: str):
    response, status = cancel_order(g.user_id, order_id)
    return jsonify(response), status