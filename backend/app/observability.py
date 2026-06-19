"""
OpenTelemetry instrumentation setup.

Initializes tracer + meter providers and wires up auto-instrumentation
for FastAPI, SQLAlchemy, asyncpg, and Redis. Exports via OTLP/HTTP to
Grafana Cloud (or any compatible OTLP backend).

All configuration is consumed from standard OTEL_* environment variables:
- OTEL_EXPORTER_OTLP_ENDPOINT (Grafana Cloud OTLP gateway URL)
- OTEL_EXPORTER_OTLP_HEADERS  (Basic auth string)
- OTEL_EXPORTER_OTLP_PROTOCOL (set to http/protobuf)
- OTEL_SERVICE_NAME           (e.g. snapit-backend)
- OTEL_RESOURCE_ATTRIBUTES    (extra labels: namespace, env, version)

If OTEL_EXPORTER_OTLP_ENDPOINT is not set, this module is a no-op,
keeping local dev simple.
"""
import logging
import os

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI, engine) -> None:
    """
    Wire up OpenTelemetry traces + metrics on the FastAPI app and SQLAlchemy
    engine. Idempotent. Safe to call once on startup.

    Skips silently if OTEL_EXPORTER_OTLP_ENDPOINT is unset, which keeps
    local dev / tests from needing a Grafana account.
    """
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.info("OTEL endpoint not set; skipping observability setup.")
        return

    # Resource attributes are picked up from OTEL_RESOURCE_ATTRIBUTES
    # plus OTEL_SERVICE_NAME, both injected via Render env vars.
    resource = Resource.create({})

    # --- Traces: BatchSpanProcessor flushes spans every few seconds ---
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    # --- Metrics: periodic OTLP push every 15 seconds ---
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(),
        export_interval_millis=60_000,
    )
    meter_provider = MeterProvider(
        resource=resource, metric_readers=[metric_reader]
    )
    metrics.set_meter_provider(meter_provider)

    # --- Auto-instrumentation: monkey-patch each library ---
    FastAPIInstrumentor.instrument_app(app)
    # SQLAlchemyInstrumentor expects the sync (underlying) engine even for
    # async engines — it instruments the dialect, not the I/O layer.
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument()

    logger.info("OpenTelemetry instrumentation enabled.")