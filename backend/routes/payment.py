import os
from flask import Blueprint, request, jsonify, redirect, g
from middleware.auth_middleware import require_auth
from controllers.payment_controller import (
    create_payment_request,
    handle_redirect,
    handle_webhook,
    query_payment_status,
    create_refund,
)

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")


@payments_bp.route("/initiate", methods=["POST"])
@require_auth
def initiate():
    data = request.get_json(silent=True) or {}
    response, status = create_payment_request(g.user_id, data)
    return jsonify(response), status


@payments_bp.route("/redirect", methods=["GET"])
def payment_redirect():
    args             = request.args.to_dict()
    response, status = handle_redirect(args)

    payment_id = args.get("payment_id", "")
    pr_id      = args.get("payment_request_id", "")

    if status == 200 and response.get("status") == "Credit":
        # Pass payment_id and pr_id back to frontend so it can call /status to confirm
        return redirect(
            f"{FRONTEND_URL}/index.html"
            f"?payment_id={payment_id}&payment_request_id={pr_id}"
        )

    order_id = response.get("order_id", "")
    return redirect(f"{FRONTEND_URL}/index.html?failed=1&order_id={order_id}")


@payments_bp.route("/webhook", methods=["POST"])
def webhook():
    form_data        = request.form.to_dict()
    response, status = handle_webhook(form_data)
    return jsonify(response), status


@payments_bp.route("/status/<payment_request_id>/<payment_id>", methods=["GET"])
@require_auth
def payment_status(payment_request_id: str, payment_id: str):
    response, status = query_payment_status(payment_request_id, payment_id)
    return jsonify(response), status


@payments_bp.route("/refund/<order_id>", methods=["POST"])
@require_auth
def refund(order_id: str):
    data             = request.get_json(silent=True) or {}
    response, status = create_refund(g.user_id, order_id, data)
    return jsonify(response), status
