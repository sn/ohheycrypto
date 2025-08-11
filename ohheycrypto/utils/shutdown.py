import logging
import signal
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handles graceful shutdown of the trading bot."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.shutdown_requested = threading.Event()
        self.shutdown_complete = threading.Event()
        self.cleanup_handlers: List[Callable] = []
        self.is_shutting_down = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # On Windows, also handle CTRL_BREAK_EVENT
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals."""
        signal_names = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM",
        }
        if hasattr(signal, "SIGBREAK"):
            signal_names[signal.SIGBREAK] = "SIGBREAK (Ctrl+Break)"

        signal_name = signal_names.get(signum, f"Signal {signum}")
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")

        if not self.is_shutting_down:
            self.is_shutting_down = True
            self.shutdown_requested.set()
            self._perform_shutdown()
        else:
            logger.warning("Shutdown already in progress. Force terminating...")
            exit(1)

    def _perform_shutdown(self):
        """Perform the actual shutdown sequence."""
        logger.info("Starting graceful shutdown sequence...")
        start_time = time.time()

        # Run cleanup handlers in reverse order
        for i, handler in enumerate(reversed(self.cleanup_handlers)):
            try:
                handler_name = getattr(
                    handler, "__name__", f"handler_{len(self.cleanup_handlers) - i}"
                )
                logger.info(f"Running cleanup handler: {handler_name}")
                handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler_name}: {e}")

        elapsed = time.time() - start_time
        logger.info(f"Graceful shutdown completed in {elapsed:.2f} seconds")
        self.shutdown_complete.set()

    def register_cleanup_handler(self, handler: Callable):
        """Register a cleanup handler to be called during shutdown."""
        self.cleanup_handlers.append(handler)
        logger.debug(f"Registered cleanup handler: {getattr(handler, '__name__', 'anonymous')}")

    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested.is_set()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown to complete."""
        return self.shutdown_complete.wait(timeout)

    @contextmanager
    def shutdown_context(self):
        """Context manager that ensures cleanup on exit."""
        try:
            yield self
        finally:
            if not self.is_shutting_down:
                logger.info("Context manager exiting, performing cleanup...")
                self._perform_shutdown()


class TradingBotShutdownManager:
    """Specialized shutdown manager for the trading bot."""

    def __init__(self, timeout_seconds: int = 30):
        self.shutdown_handler = GracefulShutdown(timeout_seconds)
        self.current_operations: List[str] = []
        self.operations_lock = threading.Lock()

    def setup_bot_cleanup(
        self, market_service=None, wallet_service=None, discord_service=None, database=None
    ):
        """Setup cleanup handlers for bot components."""

        if market_service:
            self.shutdown_handler.register_cleanup_handler(
                lambda: self._cleanup_market_service(market_service)
            )

        if wallet_service:
            self.shutdown_handler.register_cleanup_handler(
                lambda: self._cleanup_wallet_service(wallet_service)
            )

        if discord_service:
            self.shutdown_handler.register_cleanup_handler(
                lambda: self._send_shutdown_notification(discord_service)
            )

        if database:
            self.shutdown_handler.register_cleanup_handler(lambda: self._cleanup_database(database))

        # Always save state as final step
        self.shutdown_handler.register_cleanup_handler(self._save_final_state)

    def _cleanup_market_service(self, market_service):
        """Clean up market service."""
        try:
            logger.info("Cleaning up market service...")

            # Cancel any pending orders
            if hasattr(market_service, "cancel_all_open_orders"):
                market_service.cancel_all_open_orders()

            # Update circuit breaker state if needed
            if (
                hasattr(market_service, "circuit_breaker_active")
                and market_service.circuit_breaker_active
            ):
                logger.info("Circuit breaker was active during shutdown")

        except Exception as e:
            logger.error(f"Error cleaning up market service: {e}")

    def _cleanup_wallet_service(self, wallet_service):
        """Clean up wallet service."""
        try:
            logger.info("Cleaning up wallet service...")

            # Final balance sync
            if hasattr(wallet_service, "sync"):
                balances = wallet_service.sync()
                logger.info(f"Final balances: {balances}")

        except Exception as e:
            logger.error(f"Error cleaning up wallet service: {e}")

    def _send_shutdown_notification(self, discord_service):
        """Send shutdown notification to Discord."""
        try:
            logger.info("Sending shutdown notification...")

            if hasattr(discord_service, "post") and discord_service.webhook_url:
                discord_service.post(
                    channel_url=discord_service.webhook_url,
                    payload={
                        "username": "Crypto Bot",
                        "content": "🛑 Crypto Bot is shutting down",
                        "embeds": [
                            {
                                "fields": [
                                    {
                                        "name": "Shutdown Time",
                                        "value": datetime.utcnow().strftime(
                                            "%Y-%m-%d %H:%M:%S UTC"
                                        ),
                                    },
                                    {"name": "Status", "value": "Graceful shutdown completed"},
                                ]
                            }
                        ],
                    },
                )

        except Exception as e:
            logger.error(f"Error sending shutdown notification: {e}")

    def _cleanup_database(self, database):
        """Clean up database connections."""
        try:
            logger.info("Cleaning up database...")

            # Update bot state to indicate shutdown
            if hasattr(database, "update_bot_state"):
                database.update_bot_state(last_update=datetime.utcnow())

            # Clean up old data if needed
            if hasattr(database, "cleanup_old_data"):
                database.cleanup_old_data()

        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")

    def _save_final_state(self):
        """Save final bot state."""
        try:
            logger.info("Saving final bot state...")

            # This could save configuration, state, or other important data
            # Implementation depends on specific requirements

        except Exception as e:
            logger.error(f"Error saving final state: {e}")

    def register_operation(self, operation_name: str):
        """Register an ongoing operation."""
        with self.operations_lock:
            self.current_operations.append(operation_name)
            logger.debug(f"Started operation: {operation_name}")

    def unregister_operation(self, operation_name: str):
        """Unregister a completed operation."""
        with self.operations_lock:
            if operation_name in self.current_operations:
                self.current_operations.remove(operation_name)
                logger.debug(f"Completed operation: {operation_name}")

    @contextmanager
    def operation_context(self, operation_name: str):
        """Context manager for tracking operations."""
        self.register_operation(operation_name)
        try:
            yield
        finally:
            self.unregister_operation(operation_name)

    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_handler.should_shutdown()

    def wait_for_operations_to_complete(self, timeout: float = 10.0):
        """Wait for current operations to complete before shutdown."""
        start_time = time.time()

        while self.current_operations and (time.time() - start_time) < timeout:
            logger.info(f"Waiting for operations to complete: {self.current_operations}")
            time.sleep(1.0)

        if self.current_operations:
            logger.warning(f"Timeout waiting for operations: {self.current_operations}")
        else:
            logger.info("All operations completed successfully")


# Global shutdown manager instance
_shutdown_manager: Optional[TradingBotShutdownManager] = None


def get_shutdown_manager() -> TradingBotShutdownManager:
    """Get the global shutdown manager instance."""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = TradingBotShutdownManager()
    return _shutdown_manager
