from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_auth, require_role
from controllers.admin_controller import (
    get_all_products, create_product, update_product, delete_product,
    get_all_users, delete_user, block_user, unblock_user, promote_to_vendor,
    get_all_orders,
    get_admin_emails, add_admin_email, remove_admin_email,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ── Products ──────────────────────────────────────────────────────────────────

@admin_bp.route("/products", methods=["GET"])
@require_auth
@require_role("admin")
def products_list():
    data, status = get_all_products()
    return jsonify(data), status


@admin_bp.route("/products", methods=["POST"])
@require_auth
@require_role("admin")
def product_create():
    data, status = create_product(request.get_json() or {})
    return jsonify(data), status


@admin_bp.route("/products/<product_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def product_update(product_id):
    data, status = update_product(product_id, request.get_json() or {})
    return jsonify(data), status


@admin_bp.route("/products/<product_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def product_delete(product_id):
    data, status = delete_product(product_id)
    return jsonify(data), status


# ── Users ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/users", methods=["GET"])
@require_auth
@require_role("admin")
def users_list():
    data, status = get_all_users()
    return jsonify(data), status


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def user_delete(user_id):
    data, status = delete_user(user_id)
    return jsonify(data), status


@admin_bp.route("/users/<user_id>/block", methods=["POST"])
@require_auth
@require_role("admin")
def user_block(user_id):
    data, status = block_user(user_id)
    return jsonify(data), status


@admin_bp.route("/users/<user_id>/unblock", methods=["POST"])
@require_auth
@require_role("admin")
def user_unblock(user_id):
    data, status = unblock_user(user_id)
    return jsonify(data), status


@admin_bp.route("/users/<user_id>/make-vendor", methods=["POST"])
@require_auth
@require_role("admin")
def user_make_vendor(user_id):
    data, status = promote_to_vendor(user_id)
    return jsonify(data), status


# ── Orders ────────────────────────────────────────────────────────────────────

@admin_bp.route("/orders", methods=["GET"])
@require_auth
@require_role("admin")
def orders_list():
    data, status = get_all_orders()
    return jsonify(data), status


# ── Admin Email Management ────────────────────────────────────────────────────

@admin_bp.route("/admins", methods=["GET"])
@require_auth
@require_role("admin")
def admins_list():
    data, status = get_admin_emails()
    return jsonify(data), status


@admin_bp.route("/admins", methods=["POST"])
@require_auth
@require_role("admin")
def admin_add():
    data, status = add_admin_email(request.get_json() or {})
    return jsonify(data), status


@admin_bp.route("/admins/remove", methods=["POST"])
@require_auth
@require_role("admin")
def admin_remove():
    data, status = remove_admin_email(request.get_json() or {})
    return jsonify(data), status