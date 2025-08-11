"""Main bot logic for OhHeyCrypto trading bot."""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from binance.exceptions import BinanceAPIException

from ohheycrypto.config.settings import Config, get_config
from ohheycrypto.services.logging import LoggingService
from ohheycrypto.services.market import Market
from ohheycrypto.services.wallet import Wallet

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot class."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the trading bot.

        Args:
            config: Configuration object. If None, will load from environment/defaults.
        """
        self.config = config or get_config()
        self.market: Optional[Market] = None
        self.wallet: Optional[Wallet] = None
        self.running = False

    def validate_environment(self) -> bool:
        """
        Validate that all required configuration is present.

        Returns:
            True if configuration is valid, False otherwise.
        """
        if not self.config.validate_for_trading():
            return False

        # Additional validation
        if not self.config.api.binance_api_key:
            LoggingService.error("BINANCE_API_KEY not configured")
            return False

        if not self.config.api.binance_api_secret:
            LoggingService.error("BINANCE_API_SECRET not configured")
            return False

        return True

    def initialize(self) -> bool:
        """
        Initialize bot components.

        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Set environment variables for backward compatibility
            if self.config.api.binance_api_key:
                os.environ["BINANCE_API_KEY"] = self.config.api.binance_api_key
            if self.config.api.binance_api_secret:
                os.environ["BINANCE_API_SECRET"] = self.config.api.binance_api_secret
            if self.config.api.discord_webhook:
                os.environ["DISCORD_WEBHOOK"] = self.config.api.discord_webhook

            # Set trading parameters
            os.environ["BOT_SL"] = str(self.config.trading.stop_loss / 100)  # Convert percentage
            os.environ["BOT_ST"] = str(self.config.trading.sell_threshold / 100)
            os.environ["BOT_BT"] = str(self.config.trading.buy_threshold / 100)
            os.environ["BOT_FIAT"] = self.config.trading.fiat_currency
            os.environ["BOT_CRYPTO"] = self.config.trading.crypto_currency

            # Initialize components
            self.market = Market()
            self.wallet = Wallet()

            # Sync initial state
            self.market.sync()
            self.wallet.sync()

            return True

        except Exception as e:
            LoggingService.error(f"Failed to initialize bot: {e}")
            return False

    def analyze(self):
        """Analyze current market and wallet state."""
        # Display balances
        for k, v in self.wallet.balances().items():
            LoggingService.info("Balance {}: {:.8f}".format(k, v))

        # Display open orders
        for o in self.market.orders:
            if o["status"] == "NEW":
                LoggingService.success(
                    "OPEN: #{} - {} {} @ {:.4f} / ${:.2f}".format(
                        o["orderId"],
                        o["side"].upper(),
                        o["symbol"],
                        float(o["origQty"]),
                        float(o["price"]),
                    )
                )

        # Enhanced market analysis
        klines = self.market.klines(30)
        current_price = float(self.market.price().get("lastPrice", 0))

        if klines:
            rsi = self.market.calculate_rsi(klines)
            volatility = self.market.calculate_volatility(klines)
            trend = self.market.get_trend_direction()
            dynamic_buy, dynamic_sell = self.market.get_dynamic_thresholds()

            LoggingService.note("=== Enhanced Market Analysis ===")
            LoggingService.note(f"RSI: {rsi:.1f}" if rsi else "RSI: N/A")
            LoggingService.note(f"Trend: {trend.upper()}")
            LoggingService.note(f"Volatility: {volatility:.1%}")
            LoggingService.note(f"Dynamic Buy Threshold: {dynamic_buy:.1%}")
            LoggingService.note(f"Dynamic Sell Threshold: {dynamic_sell:.1%}")

        _sl = float(os.environ.get("BOT_SL", 0.03))
        LoggingService.note("Stop Loss: {:.1%}".format(_sl))
        LoggingService.note(f"Trailing Stop: {self.market.trailing_stop_percentage:.1%}")

        _p = self.market.price()
        LoggingService.note(
            "Current {} Price: ${:.2f}".format(self.market.symbol(), float(_p["lastPrice"]))
        )
        LoggingService.note(
            "High {} Price: ${:.2f}".format(self.market.symbol(), float(_p["highPrice"]))
        )
        LoggingService.note(
            "Low {} Price: ${:.2f}".format(self.market.symbol(), float(_p["lowPrice"]))
        )

    def execute_buy_order(self):
        """Execute a buy order if conditions are met."""
        if self.wallet.has(self.market.fiat) and self.market.should_buy():
            try:
                order = self.market.buy()

                if order.orderId:
                    LoggingService.order(order, self.market)
                    self.market._record_successful_order()

            except BinanceAPIException as e:
                LoggingService.error(f"Buy order failed: {e.message}")
                self.market._record_failed_order()
            except ValueError as ve:
                LoggingService.warn(f"Buy validation failed: {ve}")

    def execute_sell_order(self):
        """Execute a sell order if conditions are met."""
        if self.wallet.has(self.market.crypto) and self.market.should_sell():
            try:
                order = self.market.sell()

                if order.orderId:
                    LoggingService.order(order, self.market)
                    self.market._record_successful_order()

            except BinanceAPIException as e:
                LoggingService.error(f"Sell order failed: {e.message}")
                self.market._record_failed_order()
            except ValueError as ve:
                LoggingService.warn(f"Sell validation failed: {ve}")

    def trading_loop(self):
        """Main trading loop."""
        self.running = True
        check_interval = self.config.execution.market_check_interval

        while self.running:
            try:
                # Execute trading logic
                self.execute_buy_order()
                self.execute_sell_order()
                self.market.check_stop_loss()

                # Log circuit breaker status if active
                if self.market._is_circuit_breaker_active():
                    remaining_time = self.market.circuit_breaker_timeout - (
                        time.time() - self.market.circuit_breaker_triggered_at
                    )
                    LoggingService.warn(
                        f"Circuit breaker active: {self.market.failed_orders_count} failures, {remaining_time/60:.1f}min remaining"
                    )

                # Sleep for configured interval
                time.sleep(check_interval)

                # Sync market and wallet data
                self.market.sync()
                self.wallet.sync()

            except KeyboardInterrupt:
                LoggingService.warn("Bot stopped by user.")
                self.running = False
                break

            except requests.exceptions.ConnectionError as ce:
                LoggingService.error(f"Connection error: {ce}")
                LoggingService.warn("Sleeping for 180s before restarting.")
                time.sleep(180)
                # Re-sync after network error
                try:
                    self.market.sync()
                    self.wallet.sync()
                    LoggingService.success("Successfully reconnected and synced.")
                except Exception as sync_error:
                    LoggingService.error(f"Failed to sync after reconnection: {sync_error}")

            except BinanceAPIException as be:
                LoggingService.error(f"Binance API error: {be.message}")
                LoggingService.warn("Sleeping for 60s before continuing.")
                time.sleep(60)

            except Exception as e:
                LoggingService.error(f"Unexpected error: {e}")
                LoggingService.warn("Sleeping for 120s before continuing.")
                time.sleep(120)

    def run(self):
        """
        Main entry point for running the bot.
        """
        LoggingService.print_banner()

        if not self.validate_environment():
            LoggingService.error("Configuration validation failed. Exiting.")
            return False

        if not self.initialize():
            LoggingService.error("Bot initialization failed. Exiting.")
            return False

        # Perform initial analysis
        self.analyze()

        # Start trading loop
        self.trading_loop()

        return True

    def stop(self):
        """Stop the trading bot."""
        self.running = False
        LoggingService.warn("Stopping bot...")


def run_bot(config_path: Optional[str] = None) -> bool:
    """
    Run the trading bot with optional config file.

    Args:
        config_path: Path to configuration file (JSON)

    Returns:
        True if bot ran successfully, False otherwise.
    """
    config = None

    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            LoggingService.error(f"Configuration file not found: {config_path}")
            return False

        try:
            config = Config.load_from_file(config_file)
        except Exception as e:
            LoggingService.error(f"Failed to load configuration: {e}")
            return False
    else:
        # Load from environment variables
        config = Config.load_from_env()

    bot = TradingBot(config)
    return bot.run()
