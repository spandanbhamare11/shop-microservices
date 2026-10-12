#!/usr/bin/env bash
# Demonstrates INDEPENDENT deployment: one service is stopped, rebuilt as a new
# version and redeployed while every other service keeps running untouched.
set -e
cd "$(dirname "$0")/.."
BASE="${BASE:-http://localhost:8080}"
code () { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "== Step 1: all services healthy =="
docker ps --format 'table {{.Names}}\t{{.Status}}'
echo "Start times (must stay unchanged for untouched services):"
for c in user-service product-service payment-service order-service; do
  echo "  $c  $(docker inspect -f '{{.State.StartedAt}}' $c)"
done

echo
echo "== Step 2: stop ONLY payment-service =="
docker stop payment-service >/dev/null
echo "  GET  /users     -> $(code $BASE/users)     (still works)"
echo "  GET  /products  -> $(code $BASE/products)  (still works)"
echo "  POST /orders    -> $(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":1,"product_id":3,"quantity":1}')  (503: order service degrades gracefully, does not crash)"

echo
echo "== Step 3: ship payment-service v2 (new image tag) and redeploy it alone =="
# Make a visible change in v2: add the 'version' field to the health endpoint.
TMP=$(mktemp -d)
cp -r payment-service/. "$TMP"/
sed -i 's/status="ok"/status="ok", version="2.0"/' "$TMP/app.py"
docker build -q -t shop/payment-service:2.0 "$TMP" >/dev/null
rm -rf "$TMP"
docker rm -f payment-service >/dev/null
docker run -d --name payment-service --network shop-net shop/payment-service:2.0 >/dev/null
sleep 2

echo
echo "== Step 4: verify =="
echo "  payment-service health: $(curl -s $BASE/payments >/dev/null; docker exec gateway wget -qO- http://payment-service:5004/health)"
echo "  POST /orders    -> $(code -X POST $BASE/orders -H 'Content-Type: application/json' -d '{"user_id":2,"product_id":3,"quantity":1}')  (back to normal)"
echo "Start times after redeploy (only payment-service changed):"
for c in user-service product-service payment-service order-service; do
  echo "  $c  $(docker inspect -f '{{.State.StartedAt}}' $c)"
done
echo
echo "Done: payment-service was redeployed alone; user/product/order/gateway were never restarted."
