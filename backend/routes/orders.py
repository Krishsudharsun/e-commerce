from flask import Blueprint, request, jsonify
from controllers.product_controller import (
    get_all_products, get_product, create_product,
    update_product, delete_product,
    admin_get_stats, admin_get_all_orders,
    admin_update_order_status, admin_get_all_users,
)
from middleware.auth_middleware import require_admin

products_bp = Blueprint("products", __name__, url_prefix="/api/products")
admin_bp    = Blueprint("admin",    __name__, url_prefix="/api/admin")


# ── Public product routes ────────────────────────────────────────────────────

@products_bp.route("/", methods=["GET"])
def list_products():
    return jsonify(*get_all_products())

@products_bp.route("/", methods=["POST"])
def add_product():
    data = request.get_json(silent=True) or {}
    return jsonify(*create_product(data))

@products_bp.route("/<product_id>", methods=["GET"])
def single_product(product_id):
    return jsonify(*get_product(product_id))

@products_bp.route("/<product_id>", methods=["PUT"])
@require_admin
def edit_product(product_id):
    data = request.get_json(silent=True) or {}
    return jsonify(*update_product(product_id, data))

@products_bp.route("/<product_id>", methods=["DELETE"])
@require_admin
def remove_product(product_id):
    return jsonify(*delete_product(product_id))


# ── Admin-only routes  (prefix: /api/admin/...) ──────────────────────────────
# Kept on a SEPARATE blueprint so they never conflict with /<product_id>

@admin_bp.route("/stats", methods=["GET"])
@require_admin
def stats():
    return jsonify(*admin_get_stats())

@admin_bp.route("/orders", methods=["GET"])
@require_admin
def all_orders():
    return jsonify(*admin_get_all_orders())

@admin_bp.route("/orders/<order_id>", methods=["PATCH"])
@require_admin
def update_order(order_id):
    data   = request.get_json(silent=True) or {}
    status = data.get("status", "")
    return jsonify(*admin_update_order_status(order_id, status))

@admin_bp.route("/users", methods=["GET"])
@require_admin
def all_users():
    return jsonify(*admin_get_all_users())