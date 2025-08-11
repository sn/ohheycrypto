import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type

from binance.exceptions import BinanceAPIException
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger(__name__)


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions or (
            BinanceAPIException,
            ConnectionError,
            Timeout,
            RequestException,
        )


def retry_with_backoff(config: Optional[RetryConfig] = None) -> Callable:
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    # Check if it's a rate limit error
                    if isinstance(e, BinanceAPIException):
                        if e.code == -1003:  # TOO_MANY_REQUESTS
                            delay = config.max_delay
                            logger.warning(f"Rate limit hit. Waiting {delay} seconds before retry.")
                        elif e.code == -1021:  # TIMESTAMP_NOT_IN_RECV_WINDOW
                            delay = config.initial_delay
                            logger.warning(
                                f"Timestamp error. Retrying immediately after {delay}s delay."
                            )
                        else:
                            delay = min(
                                config.initial_delay * (config.exponential_base**attempt),
                                config.max_delay,
                            )
                    else:
                        delay = min(
                            config.initial_delay * (config.exponential_base**attempt),
                            config.max_delay,
                        )

                    if attempt < config.max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): "
                            f"{str(e)}. Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {config.max_attempts} attempts: {str(e)}"
                        )

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def is_retryable_error(exception: Exception) -> bool:
    if isinstance(exception, BinanceAPIException):
        # Retryable Binance error codes
        retryable_codes = [
            -1000,  # UNKNOWN
            -1003,  # TOO_MANY_REQUESTS
            -1015,  # TOO_MANY_NEW_ORDERS
            -1021,  # TIMESTAMP_NOT_IN_RECV_WINDOW
            -2010,  # NEW_ORDER_REJECTED
            -2011,  # CANCEL_REJECTED
        ]
        return exception.code in retryable_codes

    # Network errors are generally retryable
    if isinstance(exception, (ConnectionError, Timeout)):
        return True

    return False
