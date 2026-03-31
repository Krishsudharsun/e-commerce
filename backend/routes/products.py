from flask import Blueprint, request, jsonify, g
from controllers.product_controller import (
    get_all_products, get_product, create_product,
    update_product, delete_product,
)
from controllers.admin_controller import (
    admin_get_stats, admin_get_all_orders,
    admin_update_order_status, admin_get_all_users,
)
from middleware.auth_middleware import require_auth, require_admin, require_owner

products_bp = Blueprint("products", __name__, url_prefix="/api/products")
admin_bp    = Blueprint("admin",    __name__, url_prefix="/api/admin")


# ── Public product routes ────────────────────────────────────────────────────

@products_bp.route("/", methods=["GET"])
def list_products():
    category = request.args.get("category", "")
    search   = request.args.get("search", "")
    return jsonify(*get_all_products(category=category, search=search))


@products_bp.route("/<product_id>", methods=["GET"])
def single_product(product_id):
    return jsonify(*get_product(product_id))


@products_bp.route("/", methods=["POST"])
@require_admin
def add_product():
    data     = request.get_json(silent=True) or {}
    owner_id = None if g.user.get("role") == "owner" else g.user_id
    return jsonify(*create_product(data, owner_id=owner_id))


@products_bp.route("/<product_id>", methods=["PUT"])
@require_admin
def edit_product(product_id):
    data     = request.get_json(silent=True) or {}
    owner_id = None if g.user.get("role") == "owner" else g.user_id
    return jsonify(*update_product(product_id, data, owner_id=owner_id))


@products_bp.route("/<product_id>", methods=["DELETE"])
@require_admin
def remove_product(product_id):
    owner_id = None if g.user.get("role") == "owner" else g.user_id
    return jsonify(*delete_product(product_id, owner_id=owner_id))


# ── Admin-only routes (/api/admin/...) ───────────────────────────────────────

@admin_bp.route("/stats", methods=["GET"])
@require_admin
def stats():
    return jsonify(*admin_get_stats(caller_id=g.user_id, caller_role=g.user.get("role")))


@admin_bp.route("/orders", methods=["GET"])
@require_admin
def all_orders():
    return jsonify(*admin_get_all_orders(caller_id=g.user_id, caller_role=g.user.get("role")))


@admin_bp.route("/orders/<order_id>", methods=["PATCH"])
@require_admin
def update_order(order_id):
    data   = request.get_json(silent=True) or {}
    status = data.get("status", "")
    return jsonify(*admin_update_order_status(
        order_id, status,
        caller_id=g.user_id, caller_role=g.user.get("role")
    ))


@admin_bp.route("/users", methods=["GET"])
@require_owner
def all_users():
    return jsonify(*admin_get_all_users())
