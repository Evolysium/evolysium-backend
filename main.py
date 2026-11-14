import json
import os
import time
import uuid
from datetime import date, datetime, timezone
from functools import wraps

import stripe
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client
from werkzeug.exceptions import HTTPException

BASE = os.path.dirname(os.path.abspath(__file__))
APP_URL = os.environ.get("APP_URL", "").rstrip("/")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

MIN_CENTS, MAX_CENTS = 500, 10_000_000  # EUR 5.00 to EUR 100,000.00
# Platform fee, deducted from the recipient's share. PLACEHOLDER values: set them so the fee covers
# Stripe's processing and Connect costs for your account plus your margin.
FEE_RATE = float(os.environ.get("FEE_RATE", "0.029"))
FEE_FIXED_CENTS = int(os.environ.get("FEE_FIXED_CENTS", "30"))


def platform_fee(amount):
    return round(amount * FEE_RATE) + FEE_FIXED_CENTS
PRICES = {  # Replace with your LIVE price IDs (or set the env vars) when you go live.
    "essential": os.environ.get("PRICE_ESSENTIAL", "price_1UJi0M5Y0NKGSS7msT8FpLlI"),
    "professional": os.environ.get("PRICE_PROFESSIONAL", "price_1UJi1C5Y0NKGSS7mTI1Zaxp7"),
    "enterprise": os.environ.get("PRICE_ENTERPRISE", "price_1UJi1s5Y0NKGSS7ma6uGhJ1M"),
}

app = Flask(__name__)
CORS(app, origins=[APP_URL] if APP_URL else [])  # same-origin needs no CORS; others are blocked


# ---------- helpers ----------
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def short(i):
    return i[:8].upper()


def first(res):
    return res.data[0] if res.data else None


def log(**row):
    db.table("ledger").insert(row).execute()


def fail(msg, code=400, **extra):
    return jsonify(error=msg, **extra), code


def body():
    return request.get_json(silent=True) or {}


def valid_amount(v):
    return isinstance(v, int) and not isinstance(v, bool) and MIN_CENTS <= v <= MAX_CENTS


ENFORCE_PLANS = os.environ.get("ENFORCE_PLANS", "1") == "1"  # set to 0 while testing without subscribing
ALL_PLANS = ("essential", "professional", "enterprise")


def plan_error(me, allowed):
    """Returns an error response if the user's plan does not include the feature, else None."""
    if not ENFORCE_PLANS:
        return None
    sub = first(db.table("subscriptions").select("tier,status").eq("user_id", me["id"]).limit(1).execute())
    tier = sub["tier"] if sub and sub["status"] in ("active", "trialing") else None
    if tier in allowed:
        return None
    msg = "Choose a plan to use this feature." if tier is None else "This feature needs the Professional plan or higher."
    return fail(msg, 402, code="plan_required")


def authed(fn):
    """Verifies the Supabase access token sent by the browser."""
    @wraps(fn)
    def inner(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        try:
            user = db.auth.get_user(token).user
            me = first(db.table("profiles").select("*").eq("id", user.id).limit(1).execute())
        except Exception:
            return fail("Please sign in again.", 401)
        if not me:
            return fail("Profile not found.", 401)
        return fn(user, me, *args, **kwargs)
    return inner


def find_payee(handle, me):
    handle = str(handle or "").lower().strip()
    payee = first(db.table("profiles").select("*").eq("handle", handle).limit(1).execute())
    if not payee:
        return None, "Recipient not found."
    if payee["id"] == me["id"]:
        return None, "You cannot pay yourself."
    if not payee["payouts_enabled"]:
        return None, "This recipient has not finished payout setup yet."
    return payee, None


def sync_account(a):
    caps = a.get("capabilities") or {}
    ok = caps.get("transfers") == "active" and bool(a.get("payouts_enabled")) and bool(a.get("details_submitted"))
    db.table("profiles").update({"payouts_enabled": ok}).eq("stripe_account_id", a["id"]).execute()
    return ok


@app.errorhandler(Exception)
def on_error(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception(e)
    return fail("Something went wrong. Please try again.", 500)


# ---------- pages ----------
@app.get("/")
def home():
    return send_from_directory(os.path.join(BASE, "templates"), "index.html")


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


# ---------- Stripe webhook ----------
def on_checkout(s):
    meta = s.get("metadata") or {}
    if s.get("mode") == "subscription":
        db.table("subscriptions").upsert({
            "user_id": s.get("client_reference_id"), "tier": meta.get("tier", "essential"),
            "status": "active", "stripe_customer": s.get("customer"),
            "stripe_subscription": s.get("subscription"),
        }, on_conflict="user_id").execute()
        return
    if s.get("payment_status") != "paid":
        return
    if meta.get("kind") == "payment":
        # The status filter makes this idempotent: only the first delivery logs.
        p = first(db.table("payments").update({"status": "paid"})
                  .eq("id", meta["payment_id"]).eq("status", "pending").execute())
        if not p:
            return
        ref = "PAY-" + short(p["id"])
        log(ref=ref + "-OUT", user_id=p["payer"], counterparty=p["payee_handle"], kind="payment",
            note=p["note"], amount_cents=-p["amount_cents"], status="completed")
        log(ref=ref + "-IN", user_id=p["payee"], counterparty=p["payer_handle"], kind="payment",
            note=p["note"], amount_cents=p["amount_cents"] - p["fee_cents"], status="completed")
    elif meta.get("kind") == "agreement":
        a = first(db.table("agreements")
                  .update({"status": "funded", "payment_intent": s.get("payment_intent")})
                  .eq("id", meta["agreement_id"]).eq("status", "pending_payment").execute())
        if a:
            log(ref="AGR-" + short(a["id"]), user_id=a["payer"], counterparty=a["payee_handle"],
                kind="agreement", note=a["title"], amount_cents=-a["amount_cents"], status="held")


@app.post("/api/webhook")
def webhook():
    payload = request.get_data()
    try:
        stripe.Webhook.construct_event(payload, request.headers.get("Stripe-Signature", ""), WEBHOOK_SECRET)
    except Exception:
        return "Bad signature", 400
    ev = json.loads(payload)
    obj, kind = ev["data"]["object"], ev["type"]
    if kind == "checkout.session.completed":
        on_checkout(obj)
    elif kind == "account.updated":
        sync_account(obj)
    elif kind in ("customer.subscription.updated", "customer.subscription.deleted"):
        db.table("subscriptions").update({"status": obj["status"]}).eq("stripe_subscription", obj["id"]).execute()
    return jsonify(received=True)  # errors above return 500, so Stripe retries


# ---------- Connect onboarding ----------
@app.post("/api/connect/onboard")
@authed
def connect_onboard(user, me):
    acct_id = me.get("stripe_account_id")
    if not acct_id:
        acct = stripe.Account.create(type="express", email=user.email,
                                     capabilities={"transfers": {"requested": True}},
                                     metadata={"profile_id": me["id"]})
        acct_id = acct["id"]
        db.table("profiles").update({"stripe_account_id": acct_id}).eq("id", me["id"]).execute()
    link = stripe.AccountLink.create(account=acct_id, type="account_onboarding",
                                     refresh_url=f"{APP_URL}/?connect=refresh",
                                     return_url=f"{APP_URL}/?connect=return")
    return jsonify(url=link["url"])


@app.post("/api/connect/status")
@authed
def connect_status(user, me):
    if not me.get("stripe_account_id"):
        return jsonify(enabled=False)
    return jsonify(enabled=sync_account(stripe.Account.retrieve(me["stripe_account_id"])))


# ---------- Flow 1: direct payment (destination charge) ----------
@app.post("/api/pay")
@authed
def pay(user, me):
    blocked = plan_error(me, ALL_PLANS)
    if blocked:
        return blocked
    d = body()
    amount = d.get("amountCents")
    if not valid_amount(amount):
        return fail("Invalid amount.")
    payee, err = find_payee(d.get("payeeHandle"), me)
    if err:
        return fail(err)
    fee = platform_fee(amount)
    pay_row = first(db.table("payments").insert({
        "payer": me["id"], "payee": payee["id"], "payer_handle": me["handle"], "payee_handle": payee["handle"],
        "amount_cents": amount, "fee_cents": fee, "note": str(d.get("note") or "")[:200]}).execute())
    intent = {"transfer_data": {"destination": payee["stripe_account_id"]}}
    if fee > 0:
        intent["application_fee_amount"] = fee
    session = stripe.checkout.Session.create(
        mode="payment", customer_email=user.email,
        line_items=[{"quantity": 1, "price_data": {"currency": "eur", "unit_amount": amount,
                     "product_data": {"name": f"Payment to {payee['handle']}"}}}],
        payment_intent_data=intent,
        metadata={"kind": "payment", "payment_id": pay_row["id"]},
        success_url=f"{APP_URL}/?checkout=success", cancel_url=f"{APP_URL}/?checkout=cancel")
    db.table("payments").update({"stripe_session_id": session["id"]}).eq("id", pay_row["id"]).execute()
    return jsonify(url=session["url"])


# ---------- Flow 2: milestone escrow (charge now, transfer on approval) ----------
@app.post("/api/agreements")
@authed
def create_agreement(user, me):
    blocked = plan_error(me, ("professional", "enterprise"))
    if blocked:
        return blocked
    d = body()
    amount, title = d.get("amountCents"), str(d.get("title") or "").strip()
    if not valid_amount(amount) or not title or len(title) > 120:
        return fail("Invalid details.")
    payee, err = find_payee(d.get("payeeHandle"), me)
    if err:
        return fail(err)
    a = first(db.table("agreements").insert({
        "payer": me["id"], "payee": payee["id"], "payer_handle": me["handle"], "payee_handle": payee["handle"],
        "title": title, "amount_cents": amount}).execute())
    session = stripe.checkout.Session.create(
        mode="payment", customer_email=user.email,
        line_items=[{"quantity": 1, "price_data": {"currency": "eur", "unit_amount": amount,
                     "product_data": {"name": f"Milestone: {title}"}}}],
        payment_intent_data={"transfer_group": "AGR-" + a["id"]},
        metadata={"kind": "agreement", "agreement_id": a["id"]},
        success_url=f"{APP_URL}/?checkout=success", cancel_url=f"{APP_URL}/?checkout=cancel")
    db.table("agreements").update({"stripe_session_id": session["id"]}).eq("id", a["id"]).execute()
    return jsonify(url=session["url"])


def get_agreement(agreement_id):
    return first(db.table("agreements").select("*").eq("id", agreement_id).limit(1).execute())


@app.post("/api/agreements/<agreement_id>/release")
@authed
def release(user, me, agreement_id):
    a = get_agreement(agreement_id)
    if not a or a["payer"] != me["id"] or a["status"] != "funded":
        return fail("Agreement not available.")
    payee = first(db.table("profiles").select("stripe_account_id").eq("id", a["payee"]).limit(1).execute())
    intent = stripe.PaymentIntent.retrieve(a["payment_intent"])
    # The idempotency key makes double clicks safe: Stripe returns the same transfer.
    stripe.Transfer.create(amount=a["amount_cents"] - platform_fee(a["amount_cents"]), currency="eur", destination=payee["stripe_account_id"],
                           transfer_group="AGR-" + a["id"], source_transaction=intent["latest_charge"],
                           idempotency_key="release-" + a["id"])
    done = first(db.table("agreements").update({"status": "released", "settled_at": now_iso()})
                 .eq("id", a["id"]).eq("status", "funded").execute())
    if done:
        ref = "AGR-" + short(a["id"])
        db.table("ledger").update({"status": "released"}).eq("ref", ref).execute()
        log(ref=ref + "-IN", user_id=a["payee"], counterparty=a["payer_handle"], kind="agreement",
            note=a["title"], amount_cents=a["amount_cents"] - platform_fee(a["amount_cents"]), status="released")
    return jsonify(ok=True)


@app.post("/api/agreements/<agreement_id>/refund")  # the recipient declines the work
@authed
def refund(user, me, agreement_id):
    a = get_agreement(agreement_id)
    if not a or a["payee"] != me["id"] or a["status"] != "funded":
        return fail("Agreement not available.")
    stripe.Refund.create(payment_intent=a["payment_intent"], idempotency_key="refund-" + a["id"])
    done = first(db.table("agreements").update({"status": "refunded", "settled_at": now_iso()})
                 .eq("id", a["id"]).eq("status", "funded").execute())
    if done:
        ref = "AGR-" + short(a["id"])
        db.table("ledger").update({"status": "refunded"}).eq("ref", ref).execute()
        log(ref=ref + "-REF", user_id=a["payer"], counterparty=a["payee_handle"], kind="agreement",
            note=a["title"], amount_cents=a["amount_cents"], status="refunded")
    return jsonify(ok=True)


# ---------- Invoices (included in every plan) ----------
@app.post("/api/invoices")
@authed
def create_invoice(user, me):
    blocked = plan_error(me, ALL_PLANS)
    if blocked:
        return blocked
    d = body()
    amount = d.get("amountCents")
    client = str(d.get("client") or "").strip()[:120]
    desc = str(d.get("description") or "").strip()[:150]
    try:
        due = date.fromisoformat(str(d.get("due")))
    except ValueError:
        return fail("Invalid due date.")
    if not (isinstance(amount, int) and not isinstance(amount, bool) and 0 < amount <= MAX_CENTS) or not client or not desc:
        return fail("Invalid details.")
    ref = "INV-" + uuid.uuid4().hex[:8].upper()
    log(ref=ref, user_id=me["id"], counterparty=client, kind="invoice",
        note=f"{desc} (due {due})", amount_cents=amount, status="sent")
    return jsonify(ref=ref)


# ---------- Subscription self-service (Stripe customer portal) ----------
@app.post("/api/billing/portal")
@authed
def billing_portal(user, me):
    sub = first(db.table("subscriptions").select("stripe_customer").eq("user_id", me["id"]).limit(1).execute())
    if not sub or not sub.get("stripe_customer"):
        return fail("You do not have a subscription yet.")
    session = stripe.billing_portal.Session.create(customer=sub["stripe_customer"], return_url=f"{APP_URL}/")
    return jsonify(url=session["url"])


# ---------- Plan subscriptions ----------
@app.post("/api/payment/create-checkout-session")
@authed
def plan_checkout(user, me):
    price = PRICES.get(body().get("tier"))
    if not price:
        return fail("Unknown plan.")
    session = stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price": price, "quantity": 1}],
        customer_email=user.email, client_reference_id=user.id,
        metadata={"kind": "plan", "tier": body().get("tier")},
        success_url=f"{APP_URL}/?checkout=success", cancel_url=f"{APP_URL}/?checkout=cancel")
    return jsonify(url=session["url"])


_plans = {"t": 0, "plans": []}


@app.get("/api/plans")
def plans():
    """Live plan prices from Stripe, so the page always matches what Stripe will charge."""
    if time.time() - _plans["t"] > 300:
        out = []
        for tier, price_id in PRICES.items():
            try:
                out.append({"tier": tier, "amount": stripe.Price.retrieve(price_id)["unit_amount"]})
            except Exception:
                app.logger.warning("Could not load price for %s", tier)
        _plans.update(t=time.time(), plans=out)
    return jsonify(plans=_plans["plans"], fee={"rate": FEE_RATE, "fixed": FEE_FIXED_CENTS})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
