"""Integration tests for the shop microservices.

By default every request goes through the API gateway (http://localhost:8080),
which is how the CI pipeline runs them. To test the services directly (without
Docker) set the per-service URLs, for example:

    USERS_URL=http://localhost:5001 PRODUCTS_URL=http://localhost:5002 \
    ORDERS_URL=http://localhost:5003 PAYMENTS_URL=http://localhost:5004 pytest
"""
import os
import time

import pytest
import requests

BASE = os.getenv("BASE_URL", "http://localhost:8080")
USERS = os.getenv("USERS_URL", BASE)
PRODUCTS = os.getenv("PRODUCTS_URL", BASE)
ORDERS = os.getenv("ORDERS_URL", BASE)
PAYMENTS = os.getenv("PAYMENTS_URL", BASE)
TIMEOUT = 5


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Poll until all services answer, so tests do not race container start-up."""
    urls = [f"{USERS}/users", f"{PRODUCTS}/products", f"{ORDERS}/orders", f"{PAYMENTS}/payments"]
    deadline = time.time() + 45
    pending = list(urls)
    while pending and time.time() < deadline:
        pending = [u for u in pending if not _up(u)]
        if pending:
            time.sleep(1)
    assert not pending, f"services not reachable: {pending}"


def _up(url):
    try:
        return requests.get(url, timeout=2).status_code == 200
    except requests.RequestException:
        return False


# ---------------------------------------------------------------- user service
def test_list_users():
    r = requests.get(f"{USERS}/users", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_get_existing_user():
    r = requests.get(f"{USERS}/users/1", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_unknown_user_returns_404():
    assert requests.get(f"{USERS}/users/99999", timeout=TIMEOUT).status_code == 404


def test_create_user():
    r = requests.post(f"{USERS}/users", json={"name": "CI User", "email": "ci@example.com"}, timeout=TIMEOUT)
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert requests.get(f"{USERS}/users/{new_id}", timeout=TIMEOUT).json()["name"] == "CI User"


def test_create_user_requires_fields():
    r = requests.post(f"{USERS}/users", json={"name": "No Email"}, timeout=TIMEOUT)
    assert r.status_code == 400


# ------------------------------------------------------------- product service
def test_list_products():
    r = requests.get(f"{PRODUCTS}/products", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_get_unknown_product_returns_404():
    assert requests.get(f"{PRODUCTS}/products/99999", timeout=TIMEOUT).status_code == 404


def test_create_product():
    body = {"name": "Mouse", "price": 700, "stock": 5}
    r = requests.post(f"{PRODUCTS}/products", json=body, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 5


# ------------------------------------------------------------- payment service
def test_create_payment():
    r = requests.post(f"{PAYMENTS}/payments", json={"amount": 100}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["status"] == "SUCCESS"


def test_payment_rejects_non_positive_amount():
    r = requests.post(f"{PAYMENTS}/payments", json={"amount": 0}, timeout=TIMEOUT)
    assert r.status_code == 400


# --------------------------------------------------------------- order service
def _stock(product_id):
    return requests.get(f"{PRODUCTS}/products/{product_id}", timeout=TIMEOUT).json()["stock"]


def test_order_success_updates_stock_and_records_payment():
    before = _stock(3)
    r = requests.post(f"{ORDERS}/orders", json={"user_id": 1, "product_id": 3, "quantity": 2}, timeout=TIMEOUT)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "CONFIRMED"
    assert order["total"] == 3000.0                      # 2 x 1500
    assert _stock(3) == before - 2                       # stock reserved
    payment = requests.get(f"{PAYMENTS}/payments/{order['payment_id']}", timeout=TIMEOUT).json()
    assert payment["amount"] == 3000.0                   # payment recorded
    assert payment["status"] == "SUCCESS"


def test_order_appears_in_order_list():
    r = requests.post(f"{ORDERS}/orders", json={"user_id": 2, "product_id": 2, "quantity": 1}, timeout=TIMEOUT)
    order_id = r.json()["id"]
    ids = [o["id"] for o in requests.get(f"{ORDERS}/orders", timeout=TIMEOUT).json()]
    assert order_id in ids


def test_order_with_unknown_user_is_rejected():
    r = requests.post(f"{ORDERS}/orders", json={"user_id": 99999, "product_id": 1, "quantity": 1}, timeout=TIMEOUT)
    assert r.status_code == 400


def test_order_with_unknown_product_is_rejected():
    r = requests.post(f"{ORDERS}/orders", json={"user_id": 1, "product_id": 99999, "quantity": 1}, timeout=TIMEOUT)
    assert r.status_code == 400


def test_order_exceeding_stock_returns_409_and_keeps_stock():
    before = _stock(1)
    r = requests.post(f"{ORDERS}/orders", json={"user_id": 1, "product_id": 1, "quantity": 99999}, timeout=TIMEOUT)
    assert r.status_code == 409
    assert _stock(1) == before


def test_order_validates_input():
    r = requests.post(f"{ORDERS}/orders", json={"product_id": 1}, timeout=TIMEOUT)
    assert r.status_code == 400
