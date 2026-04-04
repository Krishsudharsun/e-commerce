from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_role
from controllers.product_controller import get_all_products, get_product, create_product

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.route("/", methods=["GET"])
def list_products():
    response, status = get_all_products()
    return jsonify(response), status


@products_bp.route("/<product_id>", methods=["GET"])
def single_product(product_id: str):
    response, status = get_product(product_id)
    return jsonify(response), status


@products_bp.route("/", methods=["POST"])
@require_role("admin")
def add_product():
    """Only admins can create products."""
    data = request.get_json(silent=True) or {}
    response, status = create_product(data)
    return jsonify(response), status
