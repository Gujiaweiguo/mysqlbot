from prometheus_client import Counter, Histogram

OPENCLAW_REQUESTS = Counter(
    "sqlbot_openclaw_requests_total",
    "Total OpenClaw adapter requests by operation, status code, and error code",
    ["operation", "status_code", "error_code"],
)

OPENCLAW_REQUEST_DURATION = Histogram(
    "sqlbot_openclaw_request_duration_seconds",
    "Duration of OpenClaw adapter requests",
    ["operation"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120),
)
