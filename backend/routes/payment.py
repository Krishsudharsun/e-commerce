"""
payment routes
==============
/api/payments/initiate                    POST  — start a payment (auth required)
/api/payments/redirect                    GET   — Instamojo sends user back here
/api/payments/webhook                     POST  — Instamojo server-to-server confirmation
/api/payments/status/<pr_id>/<pay_id>     GET   — poll/verify payment status (auth required)
/api/payments/refund/<order_id>           POST  — initiate a refund (auth required)
"""

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
    """
    Frontend calls this when user clicks 'Pay Now'.
    Returns { payment_url, order_id, payment_request_id }.
    Frontend then does window.location.href = payment_url.
    """
    data = request.get_json(silent=True) or {}
    response, status = create_payment_request(g.user_id, data)
    return jsonify(response), status


@payments_bp.route("/redirect", methods=["GET"])
def payment_redirect():
    """
    Instamojo redirects the user's browser here after payment.
    URL params: ?payment_id=...&payment_request_id=...

    We verify the actual payment status via the Instamojo API,
    then redirect the user to the frontend with the result.

    Success: FRONTEND_URL/index.html?payment_id=X&payment_request_id=Y
    Failure: FRONTEND_URL/index.html?failed=1&order_id=Z
    """
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
    """
    Instamojo POSTs the definitive payment result here (server-to-server).
    This endpoint is called regardless of whether the user returns to the
    redirect URL — it is the most reliable confirmation path.

    Must return 200 quickly. Instamojo retries if it gets a non-200.
    MAC signature is verified inside handle_webhook.
    """
    form_data        = request.form.to_dict()
    response, status = handle_webhook(form_data)
    return jsonify(response), status


@payments_bp.route("/status/<payment_request_id>/<payment_id>", methods=["GET"])
@require_auth
def payment_status(payment_request_id: str, payment_id: str):
    """
    Frontend calls this after the redirect to get the confirmed payment status.
    Also useful for polling if the user loses connection mid-payment.
    """
    response, status = query_payment_status(payment_request_id, payment_id)
    return jsonify(response), status


@payments_bp.route("/refund/<order_id>", methods=["POST"])
@require_auth
def refund(order_id: str):
    """
    Initiate a refund for a confirmed order.
    Body: { "type": "RFD", "body": "reason", "refund_amount": 99.00 }
    refund_amount is optional — omit to refund full amount.
    """
    data             = request.get_json(silent=True) or {}
    response, status = create_refund(g.user_id, order_id, data)
    return jsonify(response), status
