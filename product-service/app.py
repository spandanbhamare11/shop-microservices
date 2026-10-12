from flask import Flask, jsonify, request

app = Flask(__name__)

PRODUCTS = {
    1: {"id": 1, "name": "Laptop", "price": 55000.0, "stock": 10},
    2: {"id": 2, "name": "Headphones", "price": 2500.0, "stock": 50},
    3: {"id": 3, "name": "Keyboard", "price": 1500.0, "stock": 30},
}
_next_id = 4


@app.get("/health")
def health():
    return jsonify(service="product-service", status="ok")


@app.get("/products")
def list_products():
    return jsonify(list(PRODUCTS.values()))


@app.get("/products/<int:product_id>")
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify(error="Product not found"), 404
    return jsonify(product)


@app.post("/products")
def create_product():
    global _next_id
    data = request.get_json(silent=True) or {}
    if not data.get("name") or "price" not in data:
        return jsonify(error="name and price are required"), 400
    product = {
        "id": _next_id,
        "name": data["name"],
        "price": float(data["price"]),
        "stock": int(data.get("stock", 0)),
    }
    PRODUCTS[_next_id] = product
    _next_id += 1
    return jsonify(product), 201


@app.post("/products/<int:product_id>/reserve")
def reserve_stock(product_id):
    """Called by the order service to reduce stock when an order is placed."""
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify(error="Product not found"), 404
    qty = int((request.get_json(silent=True) or {}).get("quantity", 1))
    if product["stock"] < qty:
        return jsonify(error="Insufficient stock"), 409
    product["stock"] -= qty
    return jsonify(product)


@app.post("/products/<int:product_id>/release")
def release_stock(product_id):
    """Compensation: give stock back if a later step (payment) fails."""
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify(error="Product not found"), 404
    qty = int((request.get_json(silent=True) or {}).get("quantity", 1))
    product["stock"] += qty
    return jsonify(product)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
