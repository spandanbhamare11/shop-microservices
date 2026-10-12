#!/usr/bin/env bash
# Deploy WITHOUT docker-compose: plain docker build / network / run commands.
# Useful to show every step explicitly.
set -e
cd "$(dirname "$0")/.."

echo "==> Creating Docker network"
docker network inspect shop-net >/dev/null 2>&1 || docker network create shop-net

for svc in user product payment order; do
  echo "==> Building ${svc}-service"
  docker build -t shop/${svc}-service:1.0 ./${svc}-service
done

run_svc () {  # name image extra-args...
  docker rm -f "$1" >/dev/null 2>&1 || true
  docker run -d --name "$1" --network shop-net "${@:2}"
}

run_svc user-service    shop/user-service:1.0
run_svc product-service shop/product-service:1.0
run_svc payment-service shop/payment-service:1.0
run_svc order-service   shop/order-service:1.0

docker rm -f gateway >/dev/null 2>&1 || true
docker run -d --name gateway --network shop-net -p 8080:80 \
  -v "$(pwd)/gateway/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine

echo "==> Running containers"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo "Gateway: http://localhost:8080"
