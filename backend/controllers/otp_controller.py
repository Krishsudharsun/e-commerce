import os
import random
import string
from datetime import datetime, timedelta
from config.db import get_db

OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 10))

_twilio_client = None

def _get_twilio():
    global _twilio_client
    if _twilio_client is not None:
        return _twilio_client
    sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if sid and token:
        try:
            from twilio.rest import Client
            _twilio_client = Client(sid, token)
        except ImportError:
            print("twilio package not installed — falling back to console OTP.")
    return _twilio_client

def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

def _normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")
    return phone

def send_otp(data: dict) -> tuple[dict, int]:
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not phone and not email:
        return {"error": "phone or email is required."}, 400

    otp = _generate_otp()
    db  = get_db()
    now = datetime.utcnow()

    if phone:
        phone = _normalize_phone(phone)
        digits = phone.lstrip("+")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            return {"error": "Invalid phone number."}, 400
        db.otps.update_many({"phone": phone, "used": False}, {"$set": {"used": True}})
        db.otps.insert_one({
            "phone": phone, "otp": otp, "used": False,
            "created_at": now, "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        })
        client     = _get_twilio()
        from_phone = os.getenv("TWILIO_PHONE_NUMBER", "")
        if client and from_phone:
            try:
                client.messages.create(
                    to=phone, from_=from_phone,
                    body=f"Your FreshMart OTP is {otp}. Valid for {OTP_EXPIRY_MINUTES} minutes."
                )
            except Exception as e:
                print(f"Twilio error: {e} — OTP for {phone}: {otp}")
        else:
            print(f"[DEV] OTP for {phone}: {otp}  (expires in {OTP_EXPIRY_MINUTES} min)")
        return {"message": f"OTP sent to {phone}.", "expires_in_minutes": OTP_EXPIRY_MINUTES}, 200

    # Email OTP
    db.otps.update_many({"email": email, "used": False}, {"$set": {"used": True}})
    db.otps.insert_one({
        "email": email, "otp": otp, "used": False,
        "created_at": now, "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    })
    print(f"[DEV] OTP for {email}: {otp}  (expires in {OTP_EXPIRY_MINUTES} min)")
    return {"message": f"OTP sent to {email}.", "expires_in_minutes": OTP_EXPIRY_MINUTES}, 200


def verify_otp(data: dict) -> tuple[dict, int]:
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()
    otp   = (data.get("otp")   or "").strip()

    if not otp:
        return {"error": "otp is required."}, 400
    if not phone and not email:
        return {"error": "phone or email is required."}, 400

    if phone:
        phone = _normalize_phone(phone)

    db  = get_db()
    now = datetime.utcnow()

    query = {"used": False, "expires_at": {"$gt": now}}
    if phone:
        query["phone"] = phone
    else:
        query["email"] = email

    record = db.otps.find_one(query, sort=[("created_at", -1)])
    if not record:
        return {"error": "OTP not found or has expired. Please request a new one."}, 400
    if record["otp"] != otp:
        return {"error": "Incorrect OTP. Please try again."}, 400

    db.otps.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    return {"verified": True, "phone": phone, "email": email}, 200
