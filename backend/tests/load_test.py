"""
Dummar Platform Load Test Script
=================================

Lightweight load testing for the Dummar municipal operations API using only
Python standard library modules.

Usage:
  # Against local development server
  python -m tests.load_test --base-url http://localhost:8000

  # Against production (prefer env vars for credentials)
  export LOAD_TEST_PASSWORD='<real-password>'
  python -m tests.load_test --base-url https://api.dummar.example.com --username admin --password "$LOAD_TEST_PASSWORD"

  # With report output
  python -m tests.load_test --report-file load_test_results.json

  # Custom concurrency and request count
  python -m tests.load_test --concurrency 20 --requests-per-endpoint 100

  # Run directly
  python backend/tests/load_test.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    """Outcome of a single HTTP request."""
    status_code: int
    elapsed_ms: float
    error: Optional[str] = None


@dataclass
class EndpointReport:
    """Aggregated metrics for one endpoint."""
    method: str
    path: str
    total_requests: int = 0
    avg_ms: float = 0.0
    p95_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    error_count: int = 0
    rps: float = 0.0
    total_time_s: float = 0.0
    status_codes: Dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "total_requests": self.total_requests,
            "avg_ms": round(self.avg_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "error_count": self.error_count,
            "rps": round(self.rps, 2),
            "total_time_s": round(self.total_time_s, 3),
            "status_codes": self.status_codes,
        }


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _make_request(
    url: str,
    method: str = "GET",
    body: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> RequestResult:
    """Execute a single HTTP request and return timing + status."""
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url, data=data, headers=req_headers, method=method
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            elapsed = (time.perf_counter() - start) * 1000
            return RequestResult(status_code=resp.status, elapsed_ms=elapsed)
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            status_code=exc.code, elapsed_ms=elapsed, error=str(exc)
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(status_code=0, elapsed_ms=elapsed, error=str(exc))


def login(base_url: str, username: str, password: str) -> str:
    """Authenticate and return a bearer token."""
    url = f"{base_url}/auth/login"
    body = {"username": username, "password": password}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
            token = payload.get("access_token")
            if not token:
                raise RuntimeError(f"No access_token in response: {payload}")
            return token
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode() if exc.fp else ""
        raise RuntimeError(
            f"Login failed (HTTP {exc.code}): {body_text}"
        ) from exc


def auth_headers(token: str) -> Dict[str, str]:
    """Return Authorization header dict for a bearer token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Load-test engine
# ---------------------------------------------------------------------------

def _compute_percentile(sorted_values: List[float], pct: float) -> float:
    """Compute the *pct*-th percentile from a **sorted** list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def run_endpoint_load_test(
    url: str,
    method: str = "GET",
    body: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    concurrency: int = 10,
    num_requests: int = 50,
) -> EndpointReport:
    """Fire *num_requests* concurrent requests against a single endpoint."""
    path = url.split("://", 1)[-1]
    path = "/" + path.split("/", 1)[-1] if "/" in path else "/"

    results: List[RequestResult] = []

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(_make_request, url, method, body, headers)
            for _ in range(num_requests)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    wall_elapsed = time.perf_counter() - wall_start

    timings = sorted(r.elapsed_ms for r in results)
    status_dist: Dict[int, int] = {}
    errors = 0
    for r in results:
        status_dist[r.status_code] = status_dist.get(r.status_code, 0) + 1
        if r.error or r.status_code >= 400:
            errors += 1

    report = EndpointReport(
        method=method,
        path=path,
        total_requests=len(results),
        avg_ms=statistics.mean(timings) if timings else 0,
        p95_ms=_compute_percentile(timings, 95),
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        error_count=errors,
        rps=len(results) / wall_elapsed if wall_elapsed > 0 else 0,
        total_time_s=wall_elapsed,
        status_codes=status_dist,
    )
    return report


# ---------------------------------------------------------------------------
# Sequential workflow test (E2E throughput)
# ---------------------------------------------------------------------------

def run_sequential_workflow(
    base_url: str,
    token: str,
    iterations: int = 5,
) -> EndpointReport:
    """Test a realistic sequential workflow multiple times:

    login → create complaint → list complaints → update complaint

    Returns aggregated timing for the full workflow.
    """
    hdrs = auth_headers(token)
    results: List[RequestResult] = []

    wall_start = time.perf_counter()
    for i in range(iterations):
        workflow_start = time.perf_counter()
        workflow_error: Optional[str] = None
        last_status = 200

        # Step 1 – Create a complaint (public, no auth)
        complaint_body = {
            "full_name": f"Load Test User {i}",
            "phone": f"099{1000000 + i}",
            "complaint_type": "roads",
            "description": f"Load-test complaint #{i} – auto-generated",
            "location_text": "شارع الاختبار",
        }
        create_result = _make_request(
            f"{base_url}/complaints/",
            method="POST",
            body=complaint_body,
        )
        if create_result.error or create_result.status_code >= 400:
            workflow_error = (
                f"create complaint failed: {create_result.error or create_result.status_code}"
            )
            last_status = create_result.status_code
        else:
            complaint_id: Optional[int] = None

            # Step 2 – List complaints (auth required)
            list_result = _make_request(
                f"{base_url}/complaints/?limit=5",
                method="GET",
                headers=hdrs,
            )
            if list_result.error or list_result.status_code >= 400:
                workflow_error = (
                    f"list complaints failed: {list_result.error or list_result.status_code}"
                )
                last_status = list_result.status_code
            else:
                # Step 3 – Update complaint (get latest complaint id)
                try:
                    list_req = urllib.request.Request(
                        f"{base_url}/complaints/?limit=1",
                        headers={**{"Content-Type": "application/json"}, **hdrs},
                        method="GET",
                    )
                    with urllib.request.urlopen(list_req, timeout=30) as resp:
                        payload = json.loads(resp.read().decode())
                        items = payload.get("items", [])
                        if items:
                            complaint_id = items[0].get("id")
                except Exception:
                    complaint_id = None

                if complaint_id:
                    update_body = {
                        "status": "under_review",
                        "notes": f"Load-test update #{i}",
                    }
                    update_result = _make_request(
                        f"{base_url}/complaints/{complaint_id}",
                        method="PUT",
                        body=update_body,
                        headers=hdrs,
                    )
                    if update_result.error or update_result.status_code >= 400:
                        workflow_error = (
                            f"update complaint failed: "
                            f"{update_result.error or update_result.status_code}"
                        )
                        last_status = update_result.status_code

        elapsed = (time.perf_counter() - workflow_start) * 1000
        results.append(
            RequestResult(
                status_code=last_status if workflow_error else 200,
                elapsed_ms=elapsed,
                error=workflow_error,
            )
        )

    wall_elapsed = time.perf_counter() - wall_start
    timings = sorted(r.elapsed_ms for r in results)
    errors = sum(1 for r in results if r.error)
    status_dist: Dict[int, int] = {}
    for r in results:
        status_dist[r.status_code] = status_dist.get(r.status_code, 0) + 1

    return EndpointReport(
        method="WORKFLOW",
        path="/e2e (create→list→update)",
        total_requests=len(results),
        avg_ms=statistics.mean(timings) if timings else 0,
        p95_ms=_compute_percentile(timings, 95),
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        error_count=errors,
        rps=len(results) / wall_elapsed if wall_elapsed > 0 else 0,
        total_time_s=wall_elapsed,
        status_codes=status_dist,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

_COL_WIDTHS = (28, 10, 9, 9, 9, 9, 8, 8)
_HEADER = (
    "Endpoint",
    "Requests",
    "Avg(ms)",
    "P95(ms)",
    "Min(ms)",
    "Max(ms)",
    "Errors",
    "RPS",
)


def _fmt_row(
    label: str,
    reqs: int,
    avg: float,
    p95: float,
    mn: float,
    mx: float,
    errs: int,
    rps: float,
) -> str:
    return (
        f"{label:<{_COL_WIDTHS[0]}}"
        f"| {reqs:>{_COL_WIDTHS[1] - 2}} "
        f"| {avg:>{_COL_WIDTHS[2] - 2}.1f} "
        f"| {p95:>{_COL_WIDTHS[3] - 2}.1f} "
        f"| {mn:>{_COL_WIDTHS[4] - 2}.1f} "
        f"| {mx:>{_COL_WIDTHS[5] - 2}.1f} "
        f"| {errs:>{_COL_WIDTHS[6] - 2}} "
        f"| {rps:>{_COL_WIDTHS[7] - 2}.1f}"
    )


def print_report(
    reports: List[EndpointReport],
    base_url: str,
    concurrency: int,
) -> None:
    now = datetime.now(timezone.utc).isoformat()

    print()
    print("=== Dummar Platform Load Test Results ===")
    print(f"Base URL: {base_url}")
    print(f"Concurrency: {concurrency}")
    print(f"Date: {now}")
    print()

    header_line = _fmt_row(*_HEADER)  # type: ignore[arg-type]
    separator = "-" * len(header_line)
    print(header_line)
    print(separator)

    for r in reports:
        label = f"{r.method} {r.path}"
        if len(label) > _COL_WIDTHS[0] - 1:
            label = label[: _COL_WIDTHS[0] - 4] + "..."
        print(
            _fmt_row(
                label,
                r.total_requests,
                r.avg_ms,
                r.p95_ms,
                r.min_ms,
                r.max_ms,
                r.error_count,
                r.rps,
            )
        )
    print(separator)
    print()


def write_json_report(
    reports: List[EndpointReport],
    base_url: str,
    concurrency: int,
    filepath: str,
) -> None:
    payload = {
        "base_url": base_url,
        "concurrency": concurrency,
        "date": datetime.now(timezone.utc).isoformat(),
        "endpoints": [r.to_dict() for r in reports],
    }
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Report written to {filepath}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lightweight load test for the Dummar Platform API",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Username for authentication (default: admin)",
    )
    parser.add_argument(
        "--password",
        default="password123",
        help="Password for authentication (default: password123)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent threads (default: 10)",
    )
    parser.add_argument(
        "--requests-per-endpoint",
        type=int,
        default=50,
        help="Number of requests per endpoint (default: 50)",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Optional path to write JSON results",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    base_url: str = args.base_url.rstrip("/")
    concurrency: int = args.concurrency
    num_requests: int = args.requests_per_endpoint

    # ---- Authenticate ----
    print(f"Logging in as '{args.username}' at {base_url} ...")
    try:
        token = login(base_url, args.username, args.password)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print("Login successful – token acquired.\n")

    hdrs = auth_headers(token)
    reports: List[EndpointReport] = []

    # ---- Define endpoints ----
    endpoints: List[Dict[str, Any]] = [
        {"label": "GET /health", "url": f"{base_url}/health", "method": "GET"},
        {"label": "GET /health/ready", "url": f"{base_url}/health/ready", "method": "GET"},
        {"label": "GET /metrics", "url": f"{base_url}/metrics", "method": "GET"},
        {
            "label": "GET /complaints/",
            "url": f"{base_url}/complaints/",
            "method": "GET",
            "headers": hdrs,
        },
        {
            "label": "GET /tasks/",
            "url": f"{base_url}/tasks/",
            "method": "GET",
            "headers": hdrs,
        },
        {
            "label": "GET /contracts/",
            "url": f"{base_url}/contracts/",
            "method": "GET",
            "headers": hdrs,
        },
        {
            "label": "GET /dashboard/stats",
            "url": f"{base_url}/dashboard/stats",
            "method": "GET",
            "headers": hdrs,
        },
    ]

    # ---- Run per-endpoint load tests ----
    for ep in endpoints:
        label = ep["label"]
        print(f"Testing {label} ({num_requests} requests, {concurrency} threads) ...")
        report = run_endpoint_load_test(
            url=ep["url"],
            method=ep["method"],
            body=ep.get("body"),
            headers=ep.get("headers"),
            concurrency=concurrency,
            num_requests=num_requests,
        )
        # Override path for cleaner display
        report.path = label.split(" ", 1)[1]
        report.method = label.split(" ", 1)[0]
        reports.append(report)

    # POST /auth/login – tested separately to keep credentials out of the
    # generic endpoint list and avoid accidental logging.
    print(f"Testing POST /auth/login ({num_requests} requests, {concurrency} threads) ...")
    login_report = run_endpoint_load_test(
        url=f"{base_url}/auth/login",
        method="POST",
        body={"username": args.username, "password": args.password},
        concurrency=concurrency,
        num_requests=num_requests,
    )
    login_report.method = "POST"
    login_report.path = "/auth/login"
    reports.append(login_report)

    # POST /complaints/ – rate-limited (5/min), so use fewer requests
    complaint_requests = min(num_requests, 5)
    print(
        f"Testing POST /complaints/ ({complaint_requests} requests, "
        f"concurrency=1 due to 5/min rate limit) ..."
    )
    complaint_body = {
        "full_name": "مستخدم اختبار",
        "phone": "0991234567",
        "complaint_type": "roads",
        "description": "شكوى اختبار الحمل – يتم إنشاؤها تلقائياً",
        "location_text": "شارع الاختبار",
    }
    complaint_report = run_endpoint_load_test(
        url=f"{base_url}/complaints/",
        method="POST",
        body=complaint_body,
        concurrency=1,
        num_requests=complaint_requests,
    )
    complaint_report.method = "POST"
    complaint_report.path = "/complaints/"
    reports.append(complaint_report)

    # ---- Sequential E2E workflow ----
    print("Testing sequential E2E workflow (create→list→update) ...")
    workflow_report = run_sequential_workflow(
        base_url=base_url,
        token=token,
        iterations=5,
    )
    reports.append(workflow_report)

    # ---- Print results ----
    print_report(reports, base_url, concurrency)

    # ---- Optional JSON report ----
    if args.report_file:
        write_json_report(reports, base_url, concurrency, args.report_file)


if __name__ == "__main__":
    main()
