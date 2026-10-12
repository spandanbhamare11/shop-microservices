from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory store (each service owns its own data - no shared database)
USERS = {
    1: {"id": 1, "name": "Asha Patil", "email": "asha@example.com"},
    2: {"id": 2, "name": "Rohan Mehta", "email": "rohan@example.com"},
}
_next_id = 3


@app.get("/health")
def health():
    return jsonify(service="user-service", status="ok")


@app.get("/users")
def list_users():
    return jsonify(list(USERS.values()))


@app.get("/users/<int:user_id>")
def get_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(user)


@app.post("/users")
def create_user():
    global _next_id
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("email"):
        return jsonify(error="name and email are required"), 400
    user = {"id": _next_id, "name": data["name"], "email": data["email"]}
    USERS[_next_id] = user
    _next_id += 1
    return jsonify(user), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
