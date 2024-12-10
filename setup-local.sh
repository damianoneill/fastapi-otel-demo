#!/bin/bash

# Stricter error handling
set -euo pipefail

# Allow override via environment variables with defaults
: "${CLUSTER_NAME:=fastapi-demo}"
: "${REGISTRY_PORT:=5111}"
: "${REGISTRY_NAME:=k3d-devenv-registry}"
: "${APP_NAME:=fastapi-demo}"
: "${NAMESPACE:=default}"
: "${NO_OF_MASTERS:=1}"
: "${NO_OF_WORKERS:=2}"
: "${JAEGER_NAMESPACE:=jaeger}"
: "${JAEGER_CHART_VERSION:=2.5.12}"

# Required tools check
REQUIRED_BINARIES=("kubectl" "k3d" "docker" "helm")

check_binary() {
    local binary="$1"
    if ! command -v "$binary" &>/dev/null; then
        echo "❌ Error: $binary is not installed or not in your PATH"
        exit 1
    fi
}

# Check if docker is running
if ! docker info &>/dev/null; then
    echo "❌ Error: docker is not running"
    exit 1
fi

# Check all required binaries
for binary in "${REQUIRED_BINARIES[@]}"; do
    check_binary "$binary"
done

echo "🚀 Starting fresh setup..."

echo "🧹 Cleaning up existing resources..."

# Kill existing port forwards
if pgrep -f "kubectl port-forward.*$APP_NAME" > /dev/null; then
    echo "Killing port forwards..."
    pkill -f "kubectl port-forward.*$APP_NAME" || true
fi

# Delete existing deployments and services if a cluster exists
if kubectl cluster-info &>/dev/null; then
    echo "Removing k8s resources..."
    kubectl delete deployment "$APP_NAME" --ignore-not-found
    kubectl delete service "$APP_NAME" --ignore-not-found
fi

# Delete existing cluster if it exists
if k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo "Deleting existing cluster..."
    k3d cluster delete "$CLUSTER_NAME"
fi

echo "🌟 Creating new k3d cluster..."
k3d cluster create "$CLUSTER_NAME" \
    --agents ${NO_OF_WORKERS} \
    --servers ${NO_OF_MASTERS} \
    --port "8080:80@loadbalancer" \
    --k3s-arg "--disable=traefik@server:*" \
    --registry-use k3d-devenv-registry:5000 \
    --volume "$(pwd)/registries.yaml:/etc/rancher/k3s/registries.yaml@all"

echo "🔌 Connecting registry to cluster network..."
docker network connect "k3d-$CLUSTER_NAME" "$REGISTRY_NAME" || true

echo "🔄 Setting kubectl context..."
kubectl config use-context "k3d-$CLUSTER_NAME"

echo "⏳ Waiting for nodes to be ready..."
kubectl wait --for=condition=ready nodes --all --timeout=60s

echo "📦 Installing Jaeger..."
# Create namespace for Jaeger
kubectl create namespace "$JAEGER_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Install Jaeger
helm install jaeger \
    --namespace="$JAEGER_NAMESPACE" \
    --version "$JAEGER_CHART_VERSION" \
    --set replicas=1 \
    --set enableHttpOpenTelemetryCollector=true \
    oci://registry-1.docker.io/bitnamicharts/jaeger

echo "⏳ Waiting for Jaeger to be ready..."
kubectl rollout status deployment jaeger-query -n "$JAEGER_NAMESPACE"

echo "🔌 Setting up Jaeger port forward..."
kubectl port-forward -n "$JAEGER_NAMESPACE" service/jaeger-query 16686:16686 &
kubectl port-forward -n "$JAEGER_NAMESPACE" service/jaeger-collector 4318:4318 &

echo "🏗️ Building Docker image..."
docker build -t "localhost:$REGISTRY_PORT/$APP_NAME:latest" .

echo "⬆️ Pushing image to local registry..."
docker push "localhost:$REGISTRY_PORT/$APP_NAME:latest"

echo "🚀 Deploying to Kubernetes..."
kubectl apply -f k8s/deployment.yaml -n "$NAMESPACE"
kubectl apply -f k8s/service.yaml -n "$NAMESPACE"

echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/"$APP_NAME" -n "$NAMESPACE" --timeout=90s

echo "🔌 Setting up app port forwarding..."
CONTAINER_PORT=$(kubectl get service "$APP_NAME" -o jsonpath='{.spec.ports[0].port}' -n "$NAMESPACE")
echo "Starting port forward from localhost:8000 to $CONTAINER_PORT..."
kubectl port-forward "service/$APP_NAME" "8000:$CONTAINER_PORT" -n "$NAMESPACE" &

echo """
✅ Setup complete!
   - Cluster name: $CLUSTER_NAME
   - Registry: localhost:$REGISTRY_PORT
   - Application is accessible at: http://localhost:8000
   - Jaeger UI is accessible at: http://localhost:16686
   - Jaeger collector is accessible at: http://localhost:4318
   - To stop port forwarding, run: pkill -f 'port-forward'

To verify deployment:
   kubectl get pods -n $NAMESPACE
   kubectl get services -n $NAMESPACE
   kubectl get pods -n $JAEGER_NAMESPACE
   kubectl get services -n $JAEGER_NAMESPACE

To view Jaeger logs:
   kubectl logs -f -l app.kubernetes.io/name=jaeger -n $JAEGER_NAMESPACE
"""