import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Other services are reached by container name over the Docker network.
USER_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5001")
PRODUCT_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:5002")
PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:5004")
TIMEOUT = 3

ORDERS = {}
_next_id = 1


def release_stock(product_id, quantity):
    """Compensating action for the saga: undo the stock reservation."""
    try:
        requests.post(
            f"{PRODUCT_URL}/products/{product_id}/release",
            json={"quantity": quantity},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException:
        pass


@app.get("/health")
def health():
    return jsonify(service="order-service", status="ok")


@app.get("/orders")
def list_orders():
    return jsonify(list(ORDERS.values()))


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify(error="Order not found"), 404
    return jsonify(order)


@app.post("/orders")
def create_order():
    global _next_id
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data["user_id"])
        product_id = int(data["product_id"])
        quantity = int(data.get("quantity", 1))
    except (KeyError, ValueError):
        return jsonify(error="user_id, product_id and quantity (int) are required"), 400
    if quantity < 1:
        return jsonify(error="quantity must be >= 1"), 400

    try:
        # 1. Validate user
        r = requests.get(f"{USER_URL}/users/{user_id}", timeout=TIMEOUT)
        if r.status_code != 200:
            return jsonify(error="Invalid user"), 400

        # 2. Validate product and reserve stock
        r = requests.get(f"{PRODUCT_URL}/products/{product_id}", timeout=TIMEOUT)
        if r.status_code != 200:
            return jsonify(error="Invalid product"), 400
        product = r.json()
        total = product["price"] * quantity

        r = requests.post(
            f"{PRODUCT_URL}/products/{product_id}/reserve",
            json={"quantity": quantity},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return jsonify(error=r.json().get("error", "Could not reserve stock")), 409

        # 3. Take payment (if this fails, stock is released again)
        order_id = _next_id
        try:
            r = requests.post(
                f"{PAYMENT_URL}/payments",
                json={"order_id": order_id, "amount": total},
                timeout=TIMEOUT,
            )
        except requests.exceptions.RequestException:
            release_stock(product_id, quantity)
            raise
        if r.status_code != 201:
            release_stock(product_id, quantity)
            return jsonify(error="Payment failed"), 402
        payment = r.json()
    except requests.exceptions.RequestException:
        # A dependent service is down: fail gracefully instead of crashing.
        return jsonify(error="Dependent service unavailable"), 503

    order = {
        "id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "total": total,
        "payment_id": payment["id"],
        "status": "CONFIRMED",
    }
    ORDERS[order_id] = order
    _next_id += 1
    return jsonify(order), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
