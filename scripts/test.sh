#!/usr/bin/env bash
# End-to-end test through the API gateway.
BASE="${BASE:-http://localhost:8080}"
PASS=0; FAIL=0

check () {  # description expected_http_code actual_http_code
  if [ "$2" = "$3" ]; then echo "  PASS  $1 (HTTP $3)"; PASS=$((PASS+1))
  else echo "  FAIL  $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi
}
code () { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "== Individual services =="
check "GET  /users"          200 "$(code $BASE/users)"
check "GET  /users/1"        200 "$(code $BASE/users/1)"
check "GET  /users/999"      404 "$(code $BASE/users/999)"
check "GET  /products"       200 "$(code $BASE/products)"
check "GET  /products/1"     200 "$(code $BASE/products/1)"
check "POST /users"          201 "$(code -X POST $BASE/users -H 'Content-Type: application/json' -d '{"name":"Test","email":"t@e.com"}')"
check "POST /payments"       201 "$(code -X POST $BASE/payments -H 'Content-Type: application/json' -d '{"amount":100}')"

echo "== Order flow (order -> user + product + payment) =="
echo "  Stock before: $(curl -s $BASE/products/2)"
ORDER=$(curl -s -X POST $BASE/orders -H 'Content-Type: application/json' \
        -d '{"user_id":1,"product_id":2,"quantity":2}')
echo "  Order response: $ORDER"
check "POST /orders (valid)"        201 "$(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":1,"product_id":3,"quantity":1}')"
check "POST /orders (bad user)"     400 "$(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":999,"product_id":1,"quantity":1}')"
check "POST /orders (bad product)"  400 "$(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":1,"product_id":999,"quantity":1}')"
check "POST /orders (no stock)"     409 "$(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":1,"product_id":1,"quantity":9999}')"
echo "  Stock after:  $(curl -s $BASE/products/2)"
check "GET  /orders"                200 "$(code $BASE/orders)"

echo
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
