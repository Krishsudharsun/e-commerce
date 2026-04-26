from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from controllers.vendor_controller import (
    vendor_get_products, vendor_create_product,
    vendor_update_product, vendor_delete_product,
    vendor_get_orders,
    vendor_get_profile,
)

vendor_bp = Blueprint("vendor", __name__, url_prefix="/api/vendor")


# ── Profile ────────────────────────────────────────────────────────────────────

@vendor_bp.route("/me", methods=["GET"])
@require_role("vendor")
def get_profile():
    data, status = vendor_get_profile(g.user_id)
    return jsonify(data), status


# ── Products ───────────────────────────────────────────────────────────────────

@vendor_bp.route("/products", methods=["GET"])
@require_role("vendor")
def list_products():
    data, status = vendor_get_products(g.user_id)
    return jsonify(data), status


@vendor_bp.route("/products", methods=["POST"])
@require_role("vendor")
def create_product():
    data, status = vendor_create_product(g.user_id, request.get_json() or {})
    return jsonify(data), status


@vendor_bp.route("/products/<product_id>", methods=["PUT"])
@require_role("vendor")
def update_product(product_id):
    data, status = vendor_update_product(g.user_id, product_id, request.get_json() or {})
    return jsonify(data), status


@vendor_bp.route("/products/<product_id>", methods=["DELETE"])
@require_role("vendor")
def delete_product(product_id):
    data, status = vendor_delete_product(g.user_id, product_id)
    return jsonify(data), status


# ── Orders ─────────────────────────────────────────────────────────────────────

@vendor_bp.route("/orders", methods=["GET"])
@require_role("vendor")
def list_orders():
    data, status = vendor_get_orders(g.user_id)
    return jsonify(data), status