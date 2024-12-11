# FastAPI OpenTelemetry Demo

This project demonstrates a FastAPI application with OpenTelemetry instrumentation, running in a local Kubernetes cluster (k3d) with Jaeger for distributed tracing.

## Prerequisites

- Docker
- kubectl
- k3d
- helm
- curl
- SQLite3

## Project Structure

```
fastapi-otel-demo/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── telemetry.py
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
├── load_test.sh
├── requirements.txt
└── setup-local.sh
```

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/yourusername/fastapi-otel-demo.git
cd fastapi-otel-demo
```

2. Run the setup script:

```bash
chmod +x setup-local.sh
./setup-local.sh
```

This will:

- Create a k3d cluster
- Set up a local registry
- Deploy Jaeger
- Build and deploy the FastAPI application
- Set up port forwarding

3. Access the services:

- FastAPI application: <http://localhost:8000>
- FastAPI Swagger UI: <http://localhost:8000/docs>
- Jaeger UI: <http://localhost:16686>

## Features

### Health Check System

The application includes a sophisticated health check system that:

- Maintains a SQLite database of health check history
- Records response times and status
- Automatically cleans up old records (keeps last 24 hours)
- Provides detailed health metrics in OpenTelemetry traces

### OpenTelemetry Integration

The application is instrumented with OpenTelemetry:

- Auto-instrumentation for FastAPI endpoints
- SQLite3 instrumentation for database operations
- Detailed product catalog simulation spans
- Custom business metrics in traces
- All traces are sent to Jaeger

Example trace data features:

- Product catalog lookups
- Inventory checks
- Pricing calculations
- Database operations
- Health check metrics

## Load Testing

The repository includes a load testing script that can generate traffic to your endpoints:

```bash
chmod +x load_test.sh
./load_test.sh -c 10 -d 60
```

Options:

- `-h` Host (default: localhost)
- `-p` Port (default: 8000)
- `-d` Duration in seconds (default: 60)
- `-c` Concurrent users (default: 10)
- `-v` Verbose output

## Development

### Local Development

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application locally:

```bash
uvicorn app.main:app --reload
```

### Making Changes

1. Modify the FastAPI application in `app/main.py`
2. Update the Docker image:

```bash
docker build -t localhost:5111/fastapi-demo:latest .
docker push localhost:5111/fastapi-demo:latest
```

3. Redeploy to k3d:

```bash
kubectl rollout restart deployment fastapi-demo
```

## API Endpoints

### GET /

Returns a simple hello world message.

### GET /items/{item_id}

Simulates a product lookup with:

- Product catalog query
- Inventory availability check
- Shipping calculations
- Price computation with tax and discounts

### GET /health

Enhanced health check endpoint that:

- Records heartbeat to SQLite database
- Tracks response times
- Returns last health check status
- Maintains health check history

## Kubernetes Resources

### Deployment

The application runs as a Kubernetes Deployment with:

- 1 replica
- Health checks configured
- OpenTelemetry environment variables set
- SQLite persistence

### Service

Exposes the application within the cluster and for port-forwarding.

## Cleanup

To delete the k3d cluster and clean up all resources:

```bash
k3d cluster delete fastapi-demo
```
