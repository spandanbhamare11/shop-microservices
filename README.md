# Microservices-Based Online Shopping Application

A small online shop split into independent services, each in its own Docker container, talking over a shared Docker network.

## 1. Architecture

```
                    Client (curl / browser / Postman)
                                 |
                          localhost:8080
                                 |
                      +---------------------+
                      |  API Gateway (nginx)|
                      +---------------------+
          /users |   /products |   /orders |   /payments |
                 v             v           v             v
          +-----------+ +-------------+ +-----------+ +-------------+
          |   user    | |   product   | |   order   | |   payment   |
          |  :5001    | |   :5002     | |  :5003    | |   :5004     |
          +-----------+ +-------------+ +-----------+ +-------------+
                              ^   ^          |  |  |        ^
                              |   +----------+  |  +--------+
                              |    (reserve /   |   (create payment)
                              |     release)    |
                              +-----------------+
                                 order -> user (validate user)

          All containers are attached to the Docker bridge network: shop-net
```

| Service | Port | Responsibility | Endpoints |
|---|---|---|---|
| user-service | 5001 | Customer accounts | `GET/POST /users`, `GET /users/<id>` |
| product-service | 5002 | Catalogue and stock | `GET/POST /products`, `GET /products/<id>`, `POST /products/<id>/reserve`, `POST /products/<id>/release` |
| order-service | 5003 | Places orders; calls the other three | `GET/POST /orders`, `GET /orders/<id>` |
| payment-service | 5004 | Simulated payments | `GET/POST /payments`, `GET /payments/<id>` |
| gateway (nginx) | 8080 | Single public entry point | routes by URL prefix |

**Design principles used**
- Each service owns its own data (in-memory here; a real system would give each its own database). No shared database.
- Services communicate only through HTTP APIs, using container names as hostnames (Docker DNS on `shop-net`).
- Only the gateway publishes a port to the host; the services are reachable only inside the network.
- Order placement flow: validate user -> check product -> reserve stock -> take payment. If payment fails, stock is released (compensating action), so a failure in one service never corrupts another's data.
- Every service has a `/health` endpoint.

## 2. Prerequisites
Docker (with Docker Compose v2) and `curl`.

## 3. Run it

### Option A: Docker Compose (recommended)
```bash
docker compose up -d --build
docker compose ps
```

### Option B: plain Docker commands (shows each step explicitly)
```bash
./scripts/run-manual.sh
```
This is equivalent to:
```bash
docker network create shop-net
docker build -t shop/user-service:1.0    ./user-service
docker build -t shop/product-service:1.0 ./product-service
docker build -t shop/payment-service:1.0 ./payment-service
docker build -t shop/order-service:1.0   ./order-service
docker run -d --name user-service    --network shop-net shop/user-service:1.0
docker run -d --name product-service --network shop-net shop/product-service:1.0
docker run -d --name payment-service --network shop-net shop/payment-service:1.0
docker run -d --name order-service   --network shop-net shop/order-service:1.0
docker run -d --name gateway --network shop-net -p 8080:80 \
  -v $(pwd)/gateway/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine
```

Inspect the network:
```bash
docker network inspect shop-net
```

## 4. Test it
Automated:
```bash
./scripts/test.sh
```

Manual:
```bash
curl localhost:8080/users
curl localhost:8080/products
curl -X POST localhost:8080/orders -H 'Content-Type: application/json' \
     -d '{"user_id":1,"product_id":2,"quantity":2}'
curl localhost:8080/products/2      # stock dropped from 50 to 48
curl localhost:8080/payments        # payment recorded
curl -X POST localhost:8080/orders -H 'Content-Type: application/json' \
     -d '{"user_id":999,"product_id":1,"quantity":1}'   # 400 invalid user
```

Prove services talk over the network (order-service reaching user-service by name):
```bash
docker exec order-service python -c "import requests;print(requests.get('http://user-service:5001/health').json())"
```

## 5. Demonstrate independent deployment
```bash
./scripts/demo-independent-deploy.sh
```
The script:
1. Lists all containers and records their start times.
2. Stops **only** `payment-service`. Users and products still work; placing an order returns `503` gracefully (and stock is not lost).
3. Builds `payment-service:2.0` and starts it alone.
4. Shows orders working again and that the other containers' start times never changed, so they were never restarted.

By hand with Compose:
```bash
docker compose up -d --build payment-service   # rebuilds and redeploys only this service
docker compose stop product-service            # stop one service, others keep running
docker compose start product-service
```

## 6. Clean up
```bash
docker compose down          # if you used Compose
./scripts/cleanup.sh         # if you used run-manual.sh
```

## 7. Project structure
```
shop-microservices/
├── docker-compose.yml
├── gateway/nginx.conf
├── user-service/      (app.py, requirements.txt, Dockerfile)
├── product-service/   (app.py, requirements.txt, Dockerfile)
├── order-service/     (app.py, requirements.txt, Dockerfile)
├── payment-service/   (app.py, requirements.txt, Dockerfile)
└── scripts/           (run-manual.sh, test.sh, demo-independent-deploy.sh, cleanup.sh)
```
