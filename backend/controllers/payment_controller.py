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

_access_token     = None
_token_expires_at = None


def _get_access_token() -> str:
    global _access_token, _token_expires_at
    now = datetime.utcnow()
    if _access_token and _token_expires_at and now < _token_expires_at:
        return _access_token
    if not CLIENT_ID or not CLIENT_SEC:
        raise RuntimeError("INSTAMOJO_CLIENT_ID and INSTAMOJO_CLIENT_SECRET must be set in .env")
    r = requests.post(f"{BASE_URL}/oauth2/token/", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SEC,
    }, timeout=15)
    r.raise_for_status()
    resp = r.json()
    _access_token = resp["access_token"]
    expires_in = int(resp.get("expires_in", 36000)) - 300
    _token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    return _access_token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }


def create_payment_request(user_id: str, data: dict) -> tuple[dict, int]:
    db       = get_db()
    cart_doc = db.carts.find_one({"user_id": user_id})
    items    = cart_doc.get("items", []) if cart_doc else []

    if not items:
        return {"error": "Cart is empty."}, 400

    total      = round(sum(i["price"] * i["quantity"] for i in items), 2)
    user       = db.users.find_one({"_id": ObjectId(user_id)})
    address    = data.get("address", {})
    buyer_name = user.get("name", "Customer")
    email      = user.get("email", "") or data.get("email", "") or address.get("email", "")
    phone      = (address.get("phone", "")
                  or user.get("phone", "")
                  or data.get("phone", ""))

    if not phone:
        return {"error": "Phone number is required to process payment."}, 400
    if total < 3:
        return {"error": "Minimum order amount is ₹3."}, 400

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

    # ── MOCK MODE — skips Instamojo entirely ──────────────────────────────────
    if os.getenv("INSTAMOJO_MOCK", "false").lower() == "true":
        db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "confirmed", "payment_id": "mock_pay_" + order_id[-6:],
                      "updated_at": datetime.utcnow()}}
        )
        db.carts.update_one(
            {"user_id": user_id},
            {"$set": {"items": [], "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        frontend = os.getenv("FRONTEND_URL", "http://localhost:5500")
        return {
            "order_id":    order_id,
            "payment_url": f"{frontend}/index.html?order_id={order_id}",
        }, 201
    # ─────────────────────────────────────────────────────────────────────────

    app_url      = os.getenv("APP_URL", "http://localhost:5000")
    redirect_url = f"{app_url}/api/payments/redirect"
    webhook_url  = f"{app_url}/api/payments/webhook"

    payload = {
        "purpose":      order_id,
        "amount":       str(total),
        "buyer_name":   buyer_name,
        "email":        email,
        "phone":        phone.lstrip("+"),
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
        print("Instamojo error response:", r.json())
        return {"error": "Instamojo rejected the payment request.", "detail": r.json()}, 502

    # ── Instamojo v2 returns the object directly at top level ─────────────────
    # v1 used to wrap it as {"payment_request": {...}} — v2 does NOT do this.
    resp_json = r.json()
    mojo_data = resp_json.get("payment_request") or resp_json

    payment_request_id = mojo_data.get("id")
    longurl            = mojo_data.get("longurl")

    if not longurl:
        db.orders.delete_one({"_id": ObjectId(order_id)})
        print("Instamojo missing longurl:", resp_json)
        return {"error": "Instamojo did not return a payment URL.", "detail": resp_json}, 502
    # ─────────────────────────────────────────────────────────────────────────

    db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"payment_request_id": payment_request_id}},
    )
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


def handle_redirect(args: dict) -> tuple[dict, int]:
    payment_id         = args.get("payment_id", "")
    payment_request_id = args.get("payment_request_id", "")
    if not payment_id or not payment_request_id:
        return {"error": "Missing payment parameters."}, 400
    return query_payment_status(payment_request_id, payment_id)


def handle_webhook(form_data: dict) -> tuple[dict, int]:
    if not SALT:
        return {"error": "INSTAMOJO_SALT not configured."}, 500

    mac_provided     = form_data.get("mac", "")
    data_without_mac = {k: v for k, v in form_data.items() if k != "mac"}
    message          = "|".join(
        v for _, v in sorted(data_without_mac.items(), key=lambda x: x[0].lower())
    )
    mac_calculated = hmac.new(SALT.encode(), message.encode(), hashlib.sha1).hexdigest()

    if mac_provided != mac_calculated:
        return {"error": "MAC mismatch — possible forgery."}, 400

    status             = form_data.get("status")
    payment_request_id = form_data.get("payment_request_id")
    payment_id         = form_data.get("payment_id")

    db    = get_db()
    order = db.orders.find_one({"payment_request_id": payment_request_id})
    if not order:
        return {"error": "Order not found."}, 404

    if status == "Credit":
        db.orders.update_one({"_id": order["_id"]}, {"$set": {
            "status": "confirmed", "payment_id": payment_id, "updated_at": datetime.utcnow()
        }})
    else:
        db.orders.update_one({"_id": order["_id"]}, {"$set": {
            "status": "payment_failed", "payment_id": payment_id, "updated_at": datetime.utcnow()
        }})
        _restore_cart(db, str(order["user_id"]), order["items"])

    return {"message": "Webhook received."}, 200


def _restore_cart(db, user_id: str, items: list):
    db.carts.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def query_payment_status(payment_request_id: str, payment_id: str) -> tuple[dict, int]:
    try:
        r = requests.get(
            f"{BASE_URL}/v2/payment_requests/{payment_request_id}/{payment_id}/",
            headers=_headers(), timeout=15,
        )
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Instamojo: {str(e)}"}, 502

    if r.status_code != 200:
        return {"error": "Failed to fetch payment details."}, 502

    payment = r.json().get("payment", {})
    status  = payment.get("status")
    db      = get_db()
    order   = db.orders.find_one({"payment_request_id": payment_request_id})

    if order and order["status"] == "payment_pending":
        new_status = "confirmed" if status == "Credit" else "payment_failed"
        db.orders.update_one({"_id": order["_id"]}, {"$set": {
            "status": new_status,
            "payment_id": payment.get("payment_id"),
            "updated_at": datetime.utcnow(),
        }})
        if new_status == "payment_failed":
            _restore_cart(db, str(order["user_id"]), order.get("items", []))

    return {
        "status":   status,
        "payment":  payment,
        "order_id": str(order["_id"]) if order else None,
    }, 200


REFUND_TYPES = {
    "RFD": "Duplicate/returned/cancelled",
    "TNR": "Product not received",
    "QFL": "Customer not satisfied",
    "QNR": "Product lost in transit",
    "EWN": "Digital download issue",
    "TAN": "Event cancelled",
    "PTH": "Other",
}


def create_refund(user_id: str, order_id: str, data: dict) -> tuple[dict, int]:
    db    = get_db()
    order = db.orders.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    if not order:
        return {"error": "Order not found."}, 404
    if order.get("status") != "confirmed":
        return {"error": "Only confirmed orders can be refunded."}, 400

    payment_id = order.get("payment_id")
    if not payment_id:
        return {"error": "No payment_id on this order."}, 400

    refund_type = data.get("type", "RFD")
    if refund_type not in REFUND_TYPES:
        return {"error": f"Invalid type. Valid: {list(REFUND_TYPES)}", "types": REFUND_TYPES}, 400

    payload = {
        "type":           refund_type,
        "body":           data.get("body", "Refund requested by customer."),
        "transaction_id": data.get("transaction_id", f"TXN_{order_id}"),
    }
    if data.get("refund_amount"):
        payload["refund_amount"] = str(data["refund_amount"])

    try:
        r = requests.post(
            f"{BASE_URL}/v2/payments/{payment_id}/refund/",
            data=payload, headers=_headers(), timeout=15,
        )
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Instamojo: {str(e)}"}, 502

    if r.status_code not in (200, 201):
        return {"error": "Refund rejected by Instamojo.", "detail": r.json()}, 502

    refund = r.json().get("refund", {})
    db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": {
        "status": "refund_initiated",
        "refund_id": refund.get("id"),
        "updated_at": datetime.utcnow(),
    }})
    return {"message": "Refund initiated.", "refund": refund}, 201