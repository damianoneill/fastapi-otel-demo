import random
import time
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.status import Status, StatusCode

from .telemetry import setup_telemetry

# Initialize telemetry
setup_telemetry()

# Create FastAPI app
app = FastAPI(title="FastAPI OTEL Demo")

# Get tracer
tracer = trace.get_tracer(__name__)

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
                time.sleep(random.uniform(0.1, 0.2))  # Additional time for catalog API call

        # Simulate different product categories
        category = random.choice(["electronics", "books", "clothing", "home"])
        span.set_attribute("product.category", category)

        return {
            "item_id": item_id,
            "name": f"Item {item_id}",
            "category": category,
            "base_price": random.uniform(10, 100),
            "weight_kg": random.uniform(0.1, 5.0)
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
        with tracer.start_as_current_span("inventory.warehouse_check") as warehouse_span:
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
                "cost": round(shipping_cost, 2)
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
        discount_amount = (item["base_price"] * discount_percent / 100) if has_promotion else 0
        final_price = item["base_price"] - discount_amount + tax_amount

        span.set_attribute("price.final", final_price)
        span.set_attribute("price.discount_amount", discount_amount)

        item["pricing"] = {
            "base_price": round(item["base_price"], 2),
            "discount_percent": discount_percent,
            "discount_amount": round(discount_amount, 2),
            "tax_amount": round(tax_amount, 2),
            "final_price": round(final_price, 2)
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
            parent_span.set_attribute("item.final_price", item_data["pricing"]["final_price"])
            parent_span.set_attribute("item.in_stock", item_data["in_stock"])

            return item_data

        except Exception as e:
            parent_span.set_status(Status(StatusCode.ERROR))
            parent_span.record_exception(e)
            raise HTTPException(status_code=500, detail="Error processing item")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)