#!/usr/bin/env bash
docker rm -f gateway user-service product-service payment-service order-service 2>/dev/null || true
docker network rm shop-net 2>/dev/null || true
echo "Cleaned up containers and network."
