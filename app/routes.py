"""
PayFlow API Routes
"""

import hashlib
import os
from flask import Flask, request, jsonify
from app.models import User, Merchant, Order, Payment
from app.database import Database
from app.auth import create_token, token_required

app = Flask(__name__)
db = Database(os.environ.get("PAYFLOW_DB", "payflow.db"))

# ═══ Seed a test merchant ═══
if not db.get_all_merchants():
    m = Merchant("IKEA", "ikea@tabby.ai", "furniture")
    db.save_merchant(m)


# ═══ Health ═══
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ═══ Register ═══
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data or not data.get("name") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing required fields"}), 400

    if db.get_user_by_email(data["email"]):
        return jsonify({"error": "Email already registered"}), 400

    try:
        user = User(data["name"], data["email"], data["password"])
        db.save_user(user)
        return jsonify({"message": "User created", "user_id": user.user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ Login ═══
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing required fields"}), 400

    user = db.get_user_by_email(data["email"])
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    password_hash = hashlib.sha256(data["password"].encode()).hexdigest()
    if user["password"] != password_hash:
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user["user_id"])
    return jsonify({"token": token})


# ═══ Me ═══
@app.route("/api/me")
@token_required
def get_me(user_id):
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"name": user["name"], "email": user["email"], "balance": user["balance"]})


# ═══ Deposit ═══
@app.route("/api/deposit", methods=["POST"])
@token_required
def deposit(user_id):
    data = request.json
    if not data or not isinstance(data.get("amount"), (int, float)):
        return jsonify({"error": "Missing or invalid amount"}), 400

    user_row = db.get_user(user_id)
    if not user_row:
        return jsonify({"error": "User not found"}), 404

    try:
        user = User.from_row(user_row)
        user.deposit(data["amount"])
        db.update_user(user)
        return jsonify({"message": "Deposit successful", "balance": user.balance})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ═══ Merchants ═══
@app.route("/api/merchants")
@token_required
def get_merchants(user_id):
    rows = db.get_all_merchants()
    merchants = [
        {"merchant_id": r["merchant_id"], "name": r["name"], "category": r["category"]}
        for r in rows
    ]
    return jsonify({"merchants": merchants})


# ═══ Orders (create + list) ═══
@app.route("/api/orders", methods=["GET", "POST"])
@token_required
def orders(user_id):
    if request.method == "GET":
        rows = db.get_orders_by_user(user_id)
        result = [{"order_id": r["order_id"], "amount": r["amount"], "status": r["status"]} for r in rows]
        return jsonify(result)

    data = request.json
    if not data or not data.get("merchant_id"):
        return jsonify({"error": "Missing required fields"}), 400
    if not isinstance(data.get("amount"), (int, float)):
        return jsonify({"error": "Missing or invalid amount"}), 400

    user_row = db.get_user(user_id)
    merchant_row = db.get_merchant(data["merchant_id"])

    if not user_row:
        return jsonify({"error": "User not found"}), 404
    if not merchant_row:
        return jsonify({"error": "Merchant not found"}), 404

    try:
        user = User.from_row(user_row)
        merchant = Merchant.from_row(merchant_row)

        installments = data.get("installments", 4)
        order = Order(user, merchant, data["amount"], installments)
        db.save_order(order)

        return jsonify({
            "order_id": order.order_id,
            "amount": order.amount,
            "installment_amount": order.installment_amount,
            "status": order.status,
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ═══ Approve Order ═══
@app.route("/api/orders/<order_id>/approve", methods=["POST"])
@token_required
def approve_order(user_id, order_id):
    order_row = db.get_order(order_id)
    if not order_row:
        return jsonify({"error": "Order not found"}), 404

    if order_row["status"] != "pending":
        return jsonify({"error": f"Cannot approve order with status: {order_row['status']}"}), 400

    try:
        user_row = db.get_user(user_id)
        merchant_row = db.get_merchant(order_row["merchant_id"])
        user = User.from_row(user_row)
        merchant = Merchant.from_row(merchant_row)

        order = Order(user, merchant, order_row["amount"], order_row["num_installments"])
        order.order_id = order_row["order_id"]
        order.status = order_row["status"]
        order.approve()
        db.update_order(order)

        return jsonify({"message": "Order approved", "status": order.status})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ═══ Pay Installment ═══
@app.route("/api/orders/<order_id>/pay", methods=["POST"])
@token_required
def pay_installment(user_id, order_id):
    order_row = db.get_order(order_id)
    if not order_row:
        return jsonify({"error": "Order not found"}), 404

    if order_row["user_id"] != user_id:
        return jsonify({"error": "Not your order"}), 403

    user_row = db.get_user(user_id)
    merchant_row = db.get_merchant(order_row["merchant_id"])

    try:
        user = User.from_row(user_row)
        merchant = Merchant.from_row(merchant_row)

        order = Order.__new__(Order)
        order.order_id = order_row["order_id"]
        order.user = user
        order.merchant = merchant
        order.amount = order_row["amount"]
        order.num_installments = order_row["num_installments"]
        order.installment_amount = order_row["installment_amount"]
        order.status = order_row["status"]
        order.created_at = order_row["created_at"]

        existing = db.get_payments_by_order(order_id)
        order.payments = []
        for p in existing:
            pay = object.__new__(Payment)
            pay.payment_id = p["payment_id"]
            pay.order = order
            pay.amount = p["amount"]
            pay.status = p["status"]
            pay.created_at = p["created_at"]
            order.payments.append(pay)

        payment = order.make_payment()
        db.save_payment(payment)
        db.update_order(order)
        db.update_user(user)
        db.update_merchant(merchant)

        return jsonify({
            "message": "Payment successful",
            "remaining": order.get_remaining(),
            "installments_paid": len(order.payments),
            "installments_total": order.num_installments,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(port=8080, debug=True)
