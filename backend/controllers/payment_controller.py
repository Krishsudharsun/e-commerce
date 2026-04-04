"""
payment_controller.py
=====================
Handles all Instamojo payment operations:

  create_payment_request  →  POST /api/payments/initiate
  handle_redirect         →  GET  /api/payments/redirect   (Instamojo redirects user here)
  handle_webhook          →  POST /api/payments/webhook    (Instamojo server-to-server call)
  query_payment_status    →  GET  /api/payments/status/<pr_id>/<pay_id>
  create_refund           →  POST /api/payments/refund/<order_id>

Flow
----
1. User fills address → frontend calls POST /api/payments/initiate
2. Backend creates a pending order in MongoDB, then calls Instamojo API
3. Instamojo returns a payment_url → frontend redirects user there
4. User pays on Instamojo's hosted page
5. Instamojo POSTs result to /api/payments/webhook (server-to-server, verified by MAC)
6. Instamojo also redirects user browser to /api/payments/redirect
7. Both handlers update the order status in MongoDB
"""

import os
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from bson import ObjectId
from config.db import get_db

BASE_URL   = os.getenv("INSTAMOJO_BASE_URL", "https://test.instamojo.com")
CLIENT_ID  = os.getenv("INSTAMOJO_CLIENT_ID")
CLIENT_SEC = os.getenv("INSTAMOJO_CLIENT_SECRET")
SALT       = os.getenv("INSTAMOJO_SALT")


# ── OAuth2 token (cached, auto-refreshed) ────────────────────────────────────

_access_token     = None
_token_expires_at = None


def _get_access_token() -> str:
    """
    Instamojo uses OAuth2 client_credentials flow.
    Tokens expire in 36000 seconds (10 hrs). We cache the token and
    fetch a new one only when it expires (with a 5-min safety buffer).
    """
    global _access_token, _token_expires_at

    now = datetime.utcnow()
    if _access_token and _token_expires_at and now < _token_expires_at:
        return _access_token

    if not CLIENT_ID or not CLIENT_SEC:
        raise RuntimeError(
            "INSTAMOJO_CLIENT_ID and INSTAMOJO_CLIENT_SECRET must be set in .env"
        )

    r = requests.post(f"{BASE_URL}/oauth2/token/", data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SEC,
    }, timeout=15)
    r.raise_for_status()

    resp          = r.json()
    _access_token = resp["access_token"]
    expires_in    = int(resp.get("expires_in", 36000)) - 300   # refresh 5 min early
    _token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    return _access_token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }


# ── 1. Create Payment Request ─────────────────────────────────────────────────

def create_payment_request(user_id: str, data: dict) -> tuple[dict, int]:
    """
    Called when the user clicks "Pay Now" on the checkout modal.

    Steps:
      a. Read the user's cart from MongoDB.
      b. Create a pending order document — gives us an order_id to use as
         the payment "purpose" so we can match the webhook back to this order.
      c. Call Instamojo POST /v2/payment_requests/ with amount, buyer info, URLs.
      d. Store the returned payment_request_id on the order.
      e. Return the payment_url to the frontend — frontend does window.location = url.
    """
    db       = get_db()
    cart_doc = db.carts.find_one({"user_id": user_id})
    items    = cart_doc.get("items", []) if cart_doc else []

    if not items:
        return {"error": "Cart is empty."}, 400

    total      = round(sum(i["price"] * i["quantity"] for i in items), 2)
    user       = db.users.find_one({"_id": ObjectId(user_id)})
    address    = data.get("address", {})
    buyer_name = user.get("name", "Customer")
    email      = user.get("email", "") or data.get("email", "")
    phone      = user.get("phone", "") or data.get("phone", "")

    # Instamojo requires a phone number for Indian payments
    if not phone:
        return {"error": "Phone number is required to process payment."}, 400

    # Instamojo requires amount >= 3.00 INR
    if total < 3:
        return {"error": "Minimum order amount is ₹3."}, 400

    # Step b — insert a pending order first so we have an _id to use as purpose
    pending_order = {
        "user_id":    user_id,
        "items":      items,
        "total":      total,
        "status":     "payment_pending",
        "address":    address,
        "placed_at":  datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result   = db.orders.insert_one(pending_order)
    order_id = str(result.inserted_id)

    app_url      = os.getenv("APP_URL", "http://localhost:5000")
    redirect_url = f"{app_url}/api/payments/redirect"
    webhook_url  = f"{app_url}/api/payments/webhook"

    # Step c — call Instamojo
    payload = {
        "purpose":      order_id,           # shown on Instamojo's payment page
        "amount":       str(total),
        "buyer_name":   buyer_name,
        "email":        email,
        "phone":        phone.lstrip("+"),   # Instamojo expects digits only, no +91
        "send_email":   "False",
        "send_sms":     "False",
        "redirect_url": redirect_url,
        "webhook":      webhook_url,
        "allow_repeated_payments": "False",
    }

    try:
        r = requests.post(
            f"{BASE_URL}/v2/payment_requests/",
            data=payload,
            headers=_headers(),
            timeout=20,
        )
    except requests.exceptions.RequestException as e:
        db.orders.delete_one({"_id": ObjectId(order_id)})
        return {"error": f"Could not reach Instamojo: {str(e)}"}, 502

    if r.status_code != 201:
        db.orders.delete_one({"_id": ObjectId(order_id)})
        return {
            "error":  "Instamojo rejected the payment request.",
            "detail": r.json(),
        }, 502

    mojo_data          = r.json()["payment_request"]
    payment_request_id = mojo_data["id"]
    longurl            = mojo_data["longurl"]

    # Step d — store payment_request_id on the order
    db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"payment_request_id": payment_request_id}},
    )

    # Clear cart only AFTER successful payment request creation
    db.carts.update_one(
        {"user_id": user_id},
        {"$set": {"items": [], "updated_at": datetime.utcnow()}},
        upsert=True,
    )

    return {
        "order_id":           order_id,
        "payment_request_id": payment_request_id,
        "payment_url":        longurl,
    }, 201


# ── 2. Redirect handler ───────────────────────────────────────────────────────

def handle_redirect(args: dict) -> tuple[dict, int]:
    """
    After the user pays (or cancels), Instamojo redirects their browser to
    GET /api/payments/redirect?payment_id=...&payment_request_id=...

    We NEVER trust these query params to confirm payment — we always
    query the Instamojo API to verify the actual payment status.
    """
    payment_id         = args.get("payment_id", "")
    payment_request_id = args.get("payment_request_id", "")

    if not payment_id or not payment_request_id:
        return {"error": "Missing payment parameters."}, 400

    return query_payment_status(payment_request_id, payment_id)


# ── 3. Webhook handler ────────────────────────────────────────────────────────

def handle_webhook(form_data: dict) -> tuple[dict, int]:
    """
    Instamojo POSTs application/x-www-form-urlencoded to this endpoint
    immediately after payment, regardless of whether the user reaches
    the redirect URL. This is the RELIABLE confirmation path.

    Security: we verify the MAC signature using our INSTAMOJO_SALT.
    If MAC doesn't match, we reject the request — it may be forged.

    MAC calculation:
      1. Take all POST fields EXCEPT 'mac'
      2. Sort them alphabetically by key (case-insensitive)
      3. Join their VALUES with '|'
      4. HMAC-SHA1 that string with your salt
      5. Compare with the 'mac' field Instamojo sent
    """
    if not SALT:
        return {"error": "INSTAMOJO_SALT not configured."}, 500

    mac_provided     = form_data.get("mac", "")
    data_without_mac = {k: v for k, v in form_data.items() if k != "mac"}

    message = "|".join(
        v for _, v in sorted(data_without_mac.items(), key=lambda x: x[0].lower())
    )
    mac_calculated = hmac.new(
        SALT.encode(), message.encode(), hashlib.sha1
    ).hexdigest()

    if mac_provided != mac_calculated:
        return {"error": "MAC mismatch — possible forgery attempt."}, 400

    status             = form_data.get("status")
    payment_request_id = form_data.get("payment_request_id")
    payment_id         = form_data.get("payment_id")

    db    = get_db()
    order = db.orders.find_one({"payment_request_id": payment_request_id})

    if not order:
        return {"error": "Order not found for this payment_request_id."}, 404

    if status == "Credit":
        # Payment successful
        db.orders.update_one(
            {"_id": order["_id"]},
            {"$set": {
                "status":     "confirmed",
                "payment_id": payment_id,
                "updated_at": datetime.utcnow(),
            }},
        )
    else:
        # Payment failed or was cancelled — restore cart so user can retry
        db.orders.update_one(
            {"_id": order["_id"]},
            {"$set": {
                "status":     "payment_failed",
                "payment_id": payment_id,
                "updated_at": datetime.utcnow(),
            }},
        )
        _restore_cart(db, str(order["user_id"]), order["items"])

    return {"message": "Webhook received and processed."}, 200


def _restore_cart(db, user_id: str, items: list):
    """Put items back in cart if payment fails so user can retry."""
    db.carts.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


# ── 4. Query payment status ───────────────────────────────────────────────────

def query_payment_status(payment_request_id: str, payment_id: str) -> tuple[dict, int]:
    """
    Calls Instamojo GET /v2/payment_requests/<pr_id>/<pay_id>/ to get the
    definitive payment status. Updates the order in MongoDB accordingly.
    Used by both the redirect handler and the frontend polling endpoint.
    """
    try:
        r = requests.get(
            f"{BASE_URL}/v2/payment_requests/{payment_request_id}/{payment_id}/",
            headers=_headers(),
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Instamojo: {str(e)}"}, 502

    if r.status_code != 200:
        return {"error": "Failed to fetch payment details from Instamojo."}, 502

    payment    = r.json().get("payment", {})
    status     = payment.get("status")
    db         = get_db()
    order      = db.orders.find_one({"payment_request_id": payment_request_id})

    if order and order["status"] == "payment_pending":
        new_status = "confirmed" if status == "Credit" else "payment_failed"
        db.orders.update_one(
            {"_id": order["_id"]},
            {"$set": {
                "status":     new_status,
                "payment_id": payment.get("payment_id"),
                "updated_at": datetime.utcnow(),
            }},
        )
        if new_status == "payment_failed":
            _restore_cart(db, str(order["user_id"]), order.get("items", []))

    return {
        "status":   status,
        "payment":  payment,
        "order_id": str(order["_id"]) if order else None,
    }, 200


# ── 5. Create a refund ────────────────────────────────────────────────────────

REFUND_TYPES = {
    "RFD": "Duplicate / returned / cancelled order",
    "TNR": "Product or service not received",
    "QFL": "Customer not satisfied with quality",
    "QNR": "Product lost in transit",
    "EWN": "Digital download / access issue",
    "TAN": "Event cancelled",
    "PTH": "Other — describe in body",
}


def create_refund(user_id: str, order_id: str, data: dict) -> tuple[dict, int]:
    """
    POST /api/payments/refund/<order_id>
    Body: { "type": "RFD", "body": "Reason text", "refund_amount": 99.00 }

    refund_amount is optional — if omitted Instamojo refunds the full amount.
    """
    db    = get_db()
    order = db.orders.find_one({"_id": ObjectId(order_id), "user_id": user_id})

    if not order:
        return {"error": "Order not found."}, 404
    if order.get("status") != "confirmed":
        return {"error": "Only confirmed (paid) orders can be refunded."}, 400

    payment_id     = order.get("payment_id")
    if not payment_id:
        return {"error": "No payment_id on this order — cannot refund."}, 400

    refund_amount  = data.get("refund_amount")
    refund_type    = data.get("type", "RFD")
    reason         = data.get("body", "Refund requested by customer.")
    transaction_id = data.get("transaction_id", f"TXN_{order_id}")

    if refund_type not in REFUND_TYPES:
        return {
            "error": f"Invalid refund type. Valid types: {list(REFUND_TYPES.keys())}",
            "types": REFUND_TYPES,
        }, 400

    payload = {
        "type":           refund_type,
        "body":           reason,
        "transaction_id": transaction_id,
    }
    if refund_amount:
        payload["refund_amount"] = str(refund_amount)

    try:
        r = requests.post(
            f"{BASE_URL}/v2/payments/{payment_id}/refund/",
            data=payload,
            headers=_headers(),
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Instamojo: {str(e)}"}, 502

    if r.status_code not in (200, 201):
        return {"error": "Refund request rejected by Instamojo.", "detail": r.json()}, 502

    refund = r.json().get("refund", {})

    db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "status":     "refund_initiated",
            "refund_id":  refund.get("id"),
            "updated_at": datetime.utcnow(),
        }},
    )
    return {"message": "Refund initiated successfully.", "refund": refund}, 201
