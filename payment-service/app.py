import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

PAYMENTS = {}


@app.get("/health")
def health():
    return jsonify(service="payment-service", status="ok")


@app.get("/payments")
def list_payments():
    return jsonify(list(PAYMENTS.values()))


@app.get("/payments/<payment_id>")
def get_payment(payment_id):
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return jsonify(error="Payment not found"), 404
    return jsonify(payment)


@app.post("/payments")
def create_payment():
    """Simulated payment: succeeds for any positive amount."""
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    if amount is None or float(amount) <= 0:
        return jsonify(error="A positive amount is required"), 400
    payment = {
        "id": str(uuid.uuid4()),
        "order_id": data.get("order_id"),
        "amount": float(amount),
        "method": data.get("method", "card"),
        "status": "SUCCESS",
    }
    PAYMENTS[payment["id"]] = payment
    return jsonify(payment), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
