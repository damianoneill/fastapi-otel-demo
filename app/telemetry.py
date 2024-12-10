import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry():
    """Configure OpenTelemetry with OTLP exporter."""

    # Create a resource identifying our service
    resource = Resource.create({
        "service.name": "fastapi-demo",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "development")
    })

    # Configure the tracer
    trace.set_tracer_provider(TracerProvider(resource=resource))

    # Create OTLP exporter
    service=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    endpoint = f"{service}/v1/traces"
    print(f"OTLP Exporter Endpoint: {endpoint}")
    otlp_exporter = OTLPSpanExporter(
        endpoint=endpoint,
    )

    # Add SpanProcessor to the TracerProvider
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)