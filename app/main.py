import random
import sqlite3
import time
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.trace.status import Status, StatusCode

from .telemetry import setup_telemetry

# Initialize telemetry
setup_telemetry()

# Initialize SQLite instrumentation
SQLite3Instrumentor().instrument()

# Create FastAPI app
app = FastAPI(title="FastAPI OTEL Demo")

# Get tracer
tracer = trace.get_tracer(__name__)


# Initialize SQLite database
def init_db():
    """Initialize SQLite database with health check table."""
    with tracer.start_as_current_span("db.initialize") as span:
        try:
            conn = sqlite3.connect("health.db")
            cursor = conn.cursor()

            # Create health check table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    response_time_ms INTEGER
                )
            """)

            # Create index on timestamp
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON health_checks(timestamp)"
            )

            conn.commit()
            conn.close()

            span.set_attribute("db.operation", "initialize")
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


# Initialize database on startup
init_db()


def record_health_check(status: str, response_time_ms: int):
    """Record health check result to SQLite database."""
    with tracer.start_as_current_span("db.record_health_check") as span:
        try:
            conn = sqlite3.connect("health.db")
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO health_checks (status, response_time_ms) VALUES (?, ?)",
                (status, response_time_ms),
            )

            # Cleanup old records (keep last 24 hours)
            cursor.execute("""
                DELETE FROM health_checks
                WHERE timestamp < datetime('now', '-1 day')
            """)

            conn.commit()
            conn.close()

            span.set_attribute("db.operation", "insert")
            span.set_attribute("health.status", status)
            span.set_attribute("health.response_time_ms", response_time_ms)
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


def query_product_catalog(item_id: int) -> Dict:
    """Simulate product catalog service lookup."""
    with tracer.start_as_current_span("catalog.lookup") as span:
        span.set_attribute("catalog.service", "product-catalog-api")
        span.set_attribute("catalog.method", "GET")
        span.set_attribute("catalog.item_id", item_id)

        # Simulate service latency
        time.sleep(random.uniform(0.05, 0.1))

        # Simulate cache lookup
        with tracer.start_as_current_span("catalog.cache_check") as cache_span:
            cache_hit = random.random() > 0.3
            cache_span.set_attribute("cache.hit", cache_hit)

            if not cache_hit:
                time.sleep(
                    random.uniform(0.1, 0.2)
                )  # Additional time for catalog API call

        # Simulate different product categories
        category = random.choice(["electronics", "books", "clothing", "home"])
        span.set_attribute("product.category", category)

        return {
            "item_id": item_id,
            "name": f"Item {item_id}",
            "category": category,
            "base_price": random.uniform(10, 100),
            "weight_kg": random.uniform(0.1, 5.0),
        }


def check_inventory_availability(item: Dict) -> Dict:
    """Check inventory levels and shipping options."""
    with tracer.start_as_current_span("inventory.check") as span:
        span.set_attribute("item.id", item["item_id"])
        span.set_attribute("item.category", item["category"])

        # Simulate inventory service check
        with tracer.start_as_current_span("inventory.stock_level") as stock_span:
            time.sleep(random.uniform(0.05, 0.15))
            stock_level = random.randint(0, 100)
            stock_span.set_attribute("inventory.stock_level", stock_level)
            item["stock_level"] = stock_level
            item["in_stock"] = stock_level > 0

        # Simulate warehouse location check
        with tracer.start_as_current_span(
            "inventory.warehouse_check"
        ) as warehouse_span:
            time.sleep(random.uniform(0.03, 0.08))
            warehouse = random.choice(["EAST", "WEST", "CENTRAL"])
            warehouse_span.set_attribute("inventory.warehouse", warehouse)
            item["warehouse"] = warehouse

        # Calculate shipping estimate
        with tracer.start_as_current_span("shipping.estimate") as shipping_span:
            time.sleep(random.uniform(0.05, 0.1))
            shipping_days = random.randint(1, 5)
            shipping_cost = item["weight_kg"] * random.uniform(2, 5)
            shipping_span.set_attribute("shipping.estimated_days", shipping_days)
            shipping_span.set_attribute("shipping.cost", shipping_cost)
            item["shipping"] = {
                "estimated_days": shipping_days,
                "cost": round(shipping_cost, 2),
            }

        return item


def calculate_pricing(item: Dict) -> Dict:
    """Calculate final pricing including discounts."""
    with tracer.start_as_current_span("pricing.calculate") as span:
        span.set_attribute("item.id", item["item_id"])
        span.set_attribute("price.base", item["base_price"])

        # Check for active promotions
        with tracer.start_as_current_span("pricing.check_promotions") as promo_span:
            time.sleep(random.uniform(0.02, 0.07))
            has_promotion = random.random() > 0.7
            discount_percent = random.randint(5, 25) if has_promotion else 0
            promo_span.set_attribute("pricing.has_promotion", has_promotion)
            promo_span.set_attribute("pricing.discount_percent", discount_percent)

        # Calculate tax
        with tracer.start_as_current_span("pricing.calculate_tax") as tax_span:
            tax_rate = 0.1  # 10% tax
            tax_amount = item["base_price"] * tax_rate
            tax_span.set_attribute("pricing.tax_rate", tax_rate)
            tax_span.set_attribute("pricing.tax_amount", tax_amount)

        # Calculate final price
        discount_amount = (
            (item["base_price"] * discount_percent / 100) if has_promotion else 0
        )
        final_price = item["base_price"] - discount_amount + tax_amount

        span.set_attribute("price.final", final_price)
        span.set_attribute("price.discount_amount", discount_amount)

        item["pricing"] = {
            "base_price": round(item["base_price"], 2),
            "discount_percent": discount_percent,
            "discount_amount": round(discount_amount, 2),
            "tax_amount": round(tax_amount, 2),
            "final_price": round(final_price, 2),
        }

        return item


def validate_item(item_id: int) -> Optional[str]:
    """Validate item parameters."""
    with tracer.start_as_current_span("validation") as span:
        span.set_attribute("item.id", item_id)

        if item_id < 0:
            span.set_status(Status(StatusCode.ERROR))
            return "Item ID must be positive"

        if item_id > 1000:
            span.set_status(Status(StatusCode.ERROR))
            return "Item ID out of range"

        return None


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # Start a new parent span for the entire operation
    with tracer.start_as_current_span("get_item.process") as parent_span:
        parent_span.set_attribute("item.id", item_id)

        # Validate input
        if error := validate_item(item_id):
            raise HTTPException(status_code=400, detail=error)

        # Simulate random errors for demonstration
        if random.random() < 0.1:  # 10% chance of error
            parent_span.set_status(Status(StatusCode.ERROR))
            raise HTTPException(status_code=500, detail="Random server error")

        try:
            # Get product details
            item_data = query_product_catalog(item_id)

            # Check inventory and shipping
            item_data = check_inventory_availability(item_data)

            # Calculate final pricing
            item_data = calculate_pricing(item_data)

            # Add business metrics to span
            parent_span.set_attribute("item.category", item_data["category"])
            parent_span.set_attribute("item.warehouse", item_data["warehouse"])
            parent_span.set_attribute(
                "item.final_price", item_data["pricing"]["final_price"]
            )
            parent_span.set_attribute("item.in_stock", item_data["in_stock"])

            return item_data

        except Exception as e:
            parent_span.set_status(Status(StatusCode.ERROR))
            parent_span.record_exception(e)
            raise HTTPException(status_code=500, detail="Error processing item")


@app.get("/health")
async def health_check():
    """Enhanced health check with database heartbeat."""
    start_time = time.time()

    with tracer.start_as_current_span("health.check") as span:
        try:
            # Check database connection
            conn = sqlite3.connect("health.db")
            cursor = conn.cursor()

            # Get last health check
            cursor.execute("""
                SELECT timestamp, status, response_time_ms
                FROM health_checks
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            last_check = cursor.fetchone()

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record new health check
            record_health_check("healthy", response_time_ms)

            # Prepare response
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": response_time_ms,
            }

            if last_check:
                response["last_check"] = {
                    "timestamp": last_check[0],
                    "status": last_check[1],
                    "response_time_ms": last_check[2],
                }

            span.set_attribute("health.status", "healthy")
            span.set_attribute("health.response_time_ms", response_time_ms)
            return response

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            response_time_ms = int((time.time() - start_time) * 1000)
            try:
                record_health_check("unhealthy", response_time_ms)
            except:
                pass
            raise HTTPException(status_code=500, detail="Health check failed")


# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
