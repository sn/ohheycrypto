import logging
import os
from typing import Dict, Optional

from binance import Client
from binance.exceptions import BinanceAPIException

from ohheycrypto.utils.retry import RetryConfig, retry_with_backoff

logger = logging.getLogger(__name__)


class Wallet:
    def __init__(self):
        self.client = Client(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
        )
        self._balances: Dict[str, float] = {}
        self._sync_initial_balances()

    def _sync_initial_balances(self) -> None:
        """Sync balances on initialization with retry."""
        try:
            self._balances = self.sync()
        except Exception as e:
            logger.error(f"Failed to sync initial balances: {e}")
            self._balances = {}

    @retry_with_backoff(RetryConfig(max_attempts=5))
    def sync(self) -> Dict[str, float]:
        """
        Returns a dictionary of asset balances for the current client.
        :return: Dictionary of asset symbols to free balance amounts
        :raises: BinanceAPIException if API call fails after retries
        """
        try:
            account_info = self.client.get_account()
            if "balances" not in account_info:
                logger.error("Invalid account info structure")
                return self._balances  # Return cached balances

            _results = account_info["balances"]
            new_balances = {k["asset"]: float(k["free"]) for k in _results if float(k["free"]) > 0}

            # Update cache on successful sync
            self._balances = new_balances
            return new_balances

        except BinanceAPIException as e:
            logger.error(f"Binance API error during sync: {e.code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during sync: {e}")
            raise

    def has(self, symbol: str) -> bool:
        """
        Returns True if the current client has a balance for the given symbol.
        :param symbol: Asset symbol (e.g., 'BTC', 'USDT')
        :return: True if balance > 0, False otherwise
        """
        # Try to sync if balances are empty
        if not self._balances:
            try:
                self.sync()
            except Exception:
                logger.warning(f"Failed to sync balances, using cache for {symbol}")

        return self._balances.get(symbol, 0) > 0

    def balance(self, symbol: str) -> float:
        """
        Returns the balance for the given symbol.
        :param symbol: Asset symbol (e.g., 'BTC', 'USDT')
        :return: Balance amount or 0 if not found
        """
        # Try to sync if balances are empty
        if not self._balances:
            try:
                self.sync()
            except Exception:
                logger.warning(f"Failed to sync balances, using cache for {symbol}")

        return self._balances.get(symbol, 0)

    def balances(self) -> Dict[str, float]:
        """
        Returns a dictionary of asset balances for the current client.
        :return: Dictionary of asset symbols to balance amounts
        """
        return self._balances.copy()  # Return a copy to prevent external modifications

    def refresh_balances(self) -> Optional[Dict[str, float]]:
        """
        Force refresh balances from the API.
        :return: Updated balances or None if sync fails
        """
        try:
            return self.sync()
        except Exception as e:
            logger.error(f"Failed to refresh balances: {e}")
            return None
