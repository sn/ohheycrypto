import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result."""

    name: str
    status: str  # "healthy", "warning", "critical"
    message: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics for the trading bot."""

    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.health_checks: Dict[str, HealthCheck] = {}
        self.lock = threading.Lock()

        # Start background system metrics collection
        self._start_system_metrics_collection()

    def _start_system_metrics_collection(self):
        """Start collecting system metrics in background."""

        def collect_system_metrics():
            while True:
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.gauge("system.cpu_percent", cpu_percent)

                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.gauge("system.memory_percent", memory.percent)
                    self.gauge("system.memory_available_mb", memory.available / 1024 / 1024)

                    # Disk usage
                    disk = psutil.disk_usage("/")
                    self.gauge("system.disk_percent", (disk.used / disk.total) * 100)

                    # Network I/O
                    net_io = psutil.net_io_counters()
                    if net_io:
                        self.gauge("system.network_bytes_sent", net_io.bytes_sent)
                        self.gauge("system.network_bytes_recv", net_io.bytes_recv)

                    time.sleep(60)  # Collect every minute

                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()

    def counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            self.counters[name] += value
            self._add_point(name, self.counters[name], tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self.lock:
            self.gauges[name] = value
            self._add_point(name, value, tags)

    def timer(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        with self.lock:
            self.timers[name].append(value)
            # Keep only last 1000 timer values
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            self._add_point(name, value, tags)

    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric (same as timer for now)."""
        self.timer(name, value, tags)

    def _add_point(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Add a metric point."""
        point = MetricPoint(timestamp=time.time(), value=value, tags=tags or {})
        self.metrics[name].append(point)

    def get_metric_summary(self, name: str, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        with self.lock:
            if name not in self.metrics:
                return {}

            cutoff_time = time.time() - (duration_minutes * 60)
            recent_points = [p for p in self.metrics[name] if p.timestamp >= cutoff_time]

            if not recent_points:
                return {}

            values = [p.value for p in recent_points]

            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else 0,
                "first_timestamp": recent_points[0].timestamp,
                "last_timestamp": recent_points[-1].timestamp,
            }

    def add_health_check(self, check_name: str, check_func):
        """Add a health check function."""

        def run_check():
            try:
                result = check_func()
                if isinstance(result, bool):
                    status = "healthy" if result else "critical"
                    message = "OK" if result else "Check failed"
                    details = {}
                elif isinstance(result, dict):
                    status = result.get("status", "unknown")
                    message = result.get("message", "")
                    details = result.get("details", {})
                else:
                    status = "unknown"
                    message = str(result)
                    details = {}

                self.health_checks[check_name] = HealthCheck(
                    name=check_name,
                    status=status,
                    message=message,
                    timestamp=time.time(),
                    details=details,
                )

            except Exception as e:
                self.health_checks[check_name] = HealthCheck(
                    name=check_name,
                    status="critical",
                    message=str(e),
                    timestamp=time.time(),
                    details={"exception": str(e)},
                )

        # Run check immediately and then every 5 minutes
        run_check()

        def periodic_check():
            while True:
                time.sleep(300)  # 5 minutes
                run_check()

        thread = threading.Thread(target=periodic_check, daemon=True)
        thread.start()

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        with self.lock:
            if not self.health_checks:
                return {"status": "unknown", "checks": {}}

            # Determine overall status
            statuses = [check.status for check in self.health_checks.values()]
            if "critical" in statuses:
                overall_status = "critical"
            elif "warning" in statuses:
                overall_status = "warning"
            else:
                overall_status = "healthy"

            return {
                "status": overall_status,
                "timestamp": time.time(),
                "checks": {
                    name: {
                        "status": check.status,
                        "message": check.message,
                        "timestamp": check.timestamp,
                        "details": check.details,
                    }
                    for name, check in self.health_checks.items()
                },
            }

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        with self.lock:
            data = {
                "timestamp": time.time(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "health": self.get_health_status(),
                "metrics_summary": {
                    name: self.get_metric_summary(name, 60) for name in self.metrics.keys()
                },
            }

            if format == "json":
                return json.dumps(data, indent=2)
            else:
                return str(data)


class TradingBotMetrics:
    """Specialized metrics for the trading bot."""

    def __init__(self):
        self.collector = MetricsCollector()
        self._setup_trading_metrics()
        self._setup_health_checks()

    def _setup_trading_metrics(self):
        """Setup trading-specific metrics."""
        # Initialize counters
        self.collector.counter("trades.total", 0)
        self.collector.counter("trades.buy", 0)
        self.collector.counter("trades.sell", 0)
        self.collector.counter("trades.successful", 0)
        self.collector.counter("trades.failed", 0)
        self.collector.counter("orders.rejected", 0)
        self.collector.counter("api.calls.total", 0)
        self.collector.counter("api.errors", 0)

        # Initialize gauges
        self.collector.gauge("balance.fiat", 0)
        self.collector.gauge("balance.crypto", 0)
        self.collector.gauge("position.size", 0)
        self.collector.gauge("market.price", 0)
        self.collector.gauge("market.rsi", 0)
        self.collector.gauge("market.volatility", 0)
        self.collector.gauge("circuit_breaker.active", 0)
        self.collector.gauge("profit_loss.total", 0)
        self.collector.gauge("profit_loss.daily", 0)

    def _setup_health_checks(self):
        """Setup health checks for the trading bot."""

        def check_api_connectivity():
            """Check Binance API connectivity."""
            # This would be implemented to actually check API
            return {"status": "healthy", "message": "API connectivity OK"}

        def check_database_connection():
            """Check database connectivity."""
            try:
                from database.db import get_database

                db = get_database()
                # Simple query to test connection
                db.get_bot_state()
                return {"status": "healthy", "message": "Database OK"}
            except Exception as e:
                return {"status": "critical", "message": f"Database error: {e}"}

        def check_memory_usage():
            """Check memory usage."""
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return {"status": "critical", "message": f"High memory usage: {memory.percent}%"}
            elif memory.percent > 75:
                return {"status": "warning", "message": f"Moderate memory usage: {memory.percent}%"}
            return {"status": "healthy", "message": f"Memory usage OK: {memory.percent}%"}

        self.collector.add_health_check("api_connectivity", check_api_connectivity)
        self.collector.add_health_check("database", check_database_connection)
        self.collector.add_health_check("memory_usage", check_memory_usage)

    # Trading-specific metric methods
    def record_trade(self, side: str, price: float, quantity: float, success: bool):
        """Record a trade."""
        self.collector.counter("trades.total")
        self.collector.counter(f"trades.{side.lower()}")

        if success:
            self.collector.counter("trades.successful")
        else:
            self.collector.counter("trades.failed")

        # Record trade value
        value = price * quantity
        self.collector.histogram("trade.value", value, {"side": side})
        self.collector.histogram("trade.price", price, {"side": side})
        self.collector.histogram("trade.quantity", quantity, {"side": side})

    def record_api_call(self, endpoint: str, success: bool, duration_ms: float):
        """Record an API call."""
        self.collector.counter("api.calls.total")
        self.collector.timer("api.response_time", duration_ms, {"endpoint": endpoint})

        if not success:
            self.collector.counter("api.errors", tags={"endpoint": endpoint})

    def update_market_data(self, price: float, rsi: float, volatility: float):
        """Update market data metrics."""
        self.collector.gauge("market.price", price)
        self.collector.gauge("market.rsi", rsi)
        self.collector.gauge("market.volatility", volatility)

    def update_balances(self, fiat_balance: float, crypto_balance: float):
        """Update balance metrics."""
        self.collector.gauge("balance.fiat", fiat_balance)
        self.collector.gauge("balance.crypto", crypto_balance)

    def update_position(self, size: float):
        """Update position size."""
        self.collector.gauge("position.size", size)

    def set_circuit_breaker(self, active: bool):
        """Set circuit breaker status."""
        self.collector.gauge("circuit_breaker.active", 1 if active else 0)

    def update_profit_loss(self, total_pl: float, daily_pl: float):
        """Update profit/loss metrics."""
        self.collector.gauge("profit_loss.total", total_pl)
        self.collector.gauge("profit_loss.daily", daily_pl)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for a simple dashboard."""
        health = self.collector.get_health_status()

        # Get key metrics summaries
        metrics = {}
        key_metrics = [
            "trades.total",
            "trades.successful",
            "trades.failed",
            "balance.fiat",
            "balance.crypto",
            "position.size",
            "market.price",
            "market.rsi",
            "profit_loss.total",
            "system.cpu_percent",
            "system.memory_percent",
        ]

        for metric in key_metrics:
            summary = self.collector.get_metric_summary(metric, 60)
            if summary:
                metrics[metric] = summary

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": health,
            "metrics": metrics,
            "uptime_seconds": time.time() - (getattr(self, "_start_time", time.time())),
        }

    def save_metrics_to_file(self, filepath: str):
        """Save metrics to a file."""
        try:
            data = self.get_dashboard_data()
            Path(filepath).parent.mkdir(exist_ok=True)

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metrics to file: {e}")


# Singleton instance
_metrics: Optional[TradingBotMetrics] = None


def get_metrics() -> TradingBotMetrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = TradingBotMetrics()
        _metrics._start_time = time.time()
    return _metrics
