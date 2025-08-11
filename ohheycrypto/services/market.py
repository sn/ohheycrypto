import os
from datetime import date, timedelta
from typing import List, Optional

import numpy as np
from binance import Client

from ohheycrypto.models.order import Order
from ohheycrypto.plugins.discord import DiscordService


class Market:
    def __init__(self):
        self.stop_loss = float(os.environ.get("BOT_SL", 0.03))
        self.sell_threshold = float(os.environ.get("BOT_ST", 0.004))
        self.buy_threshold = float(os.environ.get("BOT_BT", 0.002))

        self.fiat = os.environ.get("BOT_FIAT", "USDT")
        self.crypto = os.environ.get("BOT_CRYPTO", "BTC")
        self.orders = []

        # Circuit breaker for failed orders
        self.failed_orders_count = 0
        self.max_failed_orders = 5
        self.circuit_breaker_timeout = 3600  # 1 hour
        self.circuit_breaker_triggered_at = None

        # Enhanced trading features
        self.trailing_stop_percentage = 0.02  # 2% trailing stop
        self.last_high_price = None
        self.base_buy_threshold = self.buy_threshold  # Store original
        self.base_sell_threshold = self.sell_threshold  # Store original

        # Validate configuration
        self._validate_config()

        self.client = Client(
            api_key=os.environ.get("BINANCE_API_KEY"),
            api_secret=os.environ.get("BINANCE_API_SECRET"),
        )
        self.discord = DiscordService()
        self.discord.setMarketValues(
            self.stop_loss, self.sell_threshold, self.buy_threshold, self.fiat, self.crypto
        )
        self.discord.botOnline()

    def _validate_config(self):
        """
        Validates the trading configuration parameters.
        """
        if self.stop_loss <= 0 or self.stop_loss > 0.5:
            raise ValueError(f"Stop loss must be between 0 and 0.5 (0-50%), got {self.stop_loss}")

        if self.sell_threshold <= 0 or self.sell_threshold > 0.2:
            raise ValueError(
                f"Sell threshold must be between 0 and 0.2 (0-20%), got {self.sell_threshold}"
            )

        if self.buy_threshold <= 0 or self.buy_threshold > 0.2:
            raise ValueError(
                f"Buy threshold must be between 0 and 0.2 (0-20%), got {self.buy_threshold}"
            )

        if self.stop_loss <= self.sell_threshold:
            raise ValueError(
                f"Stop loss ({self.stop_loss}) must be greater than sell threshold ({self.sell_threshold})"
            )

        if not self.fiat or not self.crypto:
            raise ValueError("Both fiat and crypto symbols must be specified")

    def _is_circuit_breaker_active(self) -> bool:
        """
        Checks if the circuit breaker is currently active.
        """
        if self.circuit_breaker_triggered_at is None:
            return False

        import time

        elapsed = time.time() - self.circuit_breaker_triggered_at
        if elapsed > self.circuit_breaker_timeout:
            # Reset circuit breaker
            self.circuit_breaker_triggered_at = None
            self.failed_orders_count = 0
            return False

        return True

    def _record_failed_order(self):
        """
        Records a failed order and potentially triggers circuit breaker.
        """
        self.failed_orders_count += 1
        if self.failed_orders_count >= self.max_failed_orders:
            import time

            self.circuit_breaker_triggered_at = time.time()

    def _record_successful_order(self):
        """
        Records a successful order and resets failure count.
        """
        self.failed_orders_count = 0

    def symbol(self) -> str:
        """
        Returns the symbol for the current client.
        """
        return "".join([self.crypto, self.fiat])

    def price(self) -> dict:
        """
        Returns the current price for the current client.
        """
        return self.client.get_ticker(symbol=self.symbol())

    def klines(self, days: int = 30) -> List[float]:
        """
        Returns a list of klines for the current client.

        :param days: int
        :return: List[float]
        """
        return [
            float(k[4])
            for k in self.client.get_historical_klines(
                self.symbol(),
                self.client.KLINE_INTERVAL_1DAY,
                (date.today() - timedelta(days=days)).isoformat(),
            )
        ]

    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index) for given prices.

        :param prices: List of closing prices
        :param period: RSI period (default 14)
        :return: RSI value or None if insufficient data
        """
        if len(prices) < period + 1:
            return None

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """
        Calculate price volatility (standard deviation of returns).

        :param prices: List of closing prices
        :param period: Period to calculate volatility over
        :return: Volatility as a decimal (e.g., 0.02 = 2%)
        """
        if len(prices) < period:
            return 0.01  # Default low volatility

        recent_prices = prices[-period:]
        returns = [
            ((recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1])
            for i in range(1, len(recent_prices))
        ]

        return np.std(returns) if returns else 0.01

    def get_dynamic_thresholds(self) -> tuple:
        """
        Calculate dynamic buy/sell thresholds based on market volatility.

        :return: Tuple of (buy_threshold, sell_threshold)
        """
        klines = self.klines(30)  # 30 days for volatility calculation
        if not klines:
            return self.base_buy_threshold, self.base_sell_threshold

        volatility = self.calculate_volatility(klines)

        # Adjust thresholds based on volatility
        # Higher volatility = wider spreads for better profit potential
        volatility_multiplier = max(1.0, min(3.0, volatility / 0.02))  # Scale 1x to 3x

        dynamic_buy = self.base_buy_threshold * volatility_multiplier
        dynamic_sell = self.base_sell_threshold * volatility_multiplier

        return dynamic_buy, dynamic_sell

    def get_trend_direction(self, period: int = 20) -> str:
        """
        Determine overall trend direction using moving averages.

        :param period: Period for moving average
        :return: 'up', 'down', or 'sideways'
        """
        klines = self.klines(period + 5)
        if len(klines) < period:
            return "sideways"

        ma_short = np.mean(klines[-10:])  # 10-day MA
        ma_long = np.mean(klines[-period:])  # 20-day MA
        current_price = klines[-1]

        if current_price > ma_short > ma_long:
            return "up"
        elif current_price < ma_short < ma_long:
            return "down"
        else:
            return "sideways"

    def should_buy(self) -> bool:
        """
        Determines whether the client should place a buy order.

        :return bool: should_buy
        """
        # Check circuit breaker
        if self._is_circuit_breaker_active():
            return False

        # Get market data for analysis
        klines = self.klines(30)
        if not klines:
            return False

        current_price = float(self.price().get("askPrice"))
        rsi = self.calculate_rsi(klines)
        trend = self.get_trend_direction()
        dynamic_buy_threshold, _ = self.get_dynamic_thresholds()

        # Update dynamic threshold
        self.buy_threshold = dynamic_buy_threshold

        last_order = self.orders[-1] if self.orders else None

        if last_order:
            last_order = Order(**last_order)

            if last_order.status == "CANCELED":
                return self._should_buy_with_indicators(current_price, rsi, trend, klines)

            if last_order.was_sold() and self.suggested_buy_price() < last_order.price:
                return self._should_buy_with_indicators(current_price, rsi, trend, klines)
            else:
                return False

        # For initial state, use enhanced analysis
        return self._should_buy_with_indicators(current_price, rsi, trend, klines)

    def _should_buy_with_indicators(
        self, current_price: float, rsi: Optional[float], trend: str, klines: List[float]
    ) -> bool:
        """
        Enhanced buy decision using technical indicators.
        """
        # RSI oversold condition (strong buy signal)
        if rsi and rsi < 30:
            return True

        # Don't buy if RSI is overbought
        if rsi and rsi > 70:
            return False

        # Trend-based decisions
        if trend == "down":
            # In downtrend, wait for stronger dip
            recent_high = max(klines[-7:])
            return current_price <= recent_high * (1 - self.buy_threshold * 1.5)
        elif trend == "up":
            # In uptrend, be more aggressive on small dips
            recent_high = max(klines[-3:])
            return current_price <= recent_high * (1 - self.buy_threshold * 0.7)
        else:
            # Sideways market - use standard logic
            recent_high = max(klines[-7:])
            return current_price <= recent_high * (1 - self.buy_threshold)

    def should_sell(self) -> bool:
        """
        Determines whether the client should place a sell order.

        :return bool: should_sell
        """
        # Check circuit breaker
        if self._is_circuit_breaker_active():
            return False

        # Get market data for analysis
        klines = self.klines(30)
        if not klines:
            return False

        current_price = float(self.price().get("askPrice"))
        rsi = self.calculate_rsi(klines)
        trend = self.get_trend_direction()
        _, dynamic_sell_threshold = self.get_dynamic_thresholds()

        # Update dynamic threshold
        self.sell_threshold = dynamic_sell_threshold

        last_order = self.orders[-1] if self.orders else None

        if last_order:
            last_order = Order(**last_order)

            if last_order.status == "CANCELED":
                return self._should_sell_with_indicators(current_price, rsi, trend, last_order)

            if last_order.was_bought():
                # Check trailing stop-loss first
                if self._check_trailing_stop(current_price, last_order.price):
                    return True

                # Then check enhanced sell conditions
                if self.suggested_sell_price() > last_order.price:
                    return self._should_sell_with_indicators(current_price, rsi, trend, last_order)

            return False

        return False

    def _should_sell_with_indicators(
        self, current_price: float, rsi: Optional[float], trend: str, last_order: Order
    ) -> bool:
        """
        Enhanced sell decision using technical indicators.
        """
        profit_percentage = (current_price - last_order.price) / last_order.price

        # RSI overbought condition (strong sell signal)
        if rsi and rsi > 70:
            return True

        # Don't sell if RSI is oversold (might bounce back)
        if rsi and rsi < 30:
            return False

        # Trend-based decisions
        if trend == "up":
            # In uptrend, hold longer for bigger profits
            return profit_percentage >= self.sell_threshold * 1.5
        elif trend == "down":
            # In downtrend, take profits quicker
            return profit_percentage >= self.sell_threshold * 0.7
        else:
            # Sideways market - use standard logic
            return profit_percentage >= self.sell_threshold

    def _check_trailing_stop(self, current_price: float, buy_price: float) -> bool:
        """
        Check if trailing stop-loss should trigger.
        """
        # Update highest price seen since purchase
        if self.last_high_price is None or current_price > self.last_high_price:
            self.last_high_price = current_price

        # Only check trailing stop if we're in profit
        if current_price <= buy_price:
            return False

        # Calculate trailing stop price
        trailing_stop_price = self.last_high_price * (1 - self.trailing_stop_percentage)

        # Trigger if current price drops below trailing stop
        return current_price <= trailing_stop_price

    def fees(self) -> dict:
        """
        Returns the fees for the current client.

        :return fees: dict
        """
        return self.client.get_trade_fee(symbol=self.symbol())

    def suggested_buy_price(self) -> float:
        """
        Calculate the suggested buy price based on the current price and buy threshold.

        :return float: price
        """
        _price = float(self.price().get("askPrice"))

        return round(_price - (_price * self.buy_threshold), 2)

    def suggested_sell_price(self) -> float:
        """
        Calculate the suggested sell price based on the current price and sell threshold.

        :return float: price
        """
        _price = float(self.price().get("askPrice"))

        return round(_price + (_price * self.sell_threshold), 2)

    def ready_for_orders(self) -> bool:
        """
        Determines whether the client is ready to place new orders by checking if orders are in progress.

        :return bool: ready
        """
        for o in self.client.get_all_orders(symbol=self.symbol(), limit=100):
            if o["status"] == "NEW":
                return False
        return True

    def sync(self):
        """
        Syncs the client's orders for a given symbol, but ignores canceled orders.
        """
        # Clear existing orders to prevent duplicates
        self.orders.clear()
        for o in self.client.get_all_orders(symbol=self.symbol(), limit=100):
            if o["status"] != "CANCELED":
                self.orders.append(o)

    def calculate_position_size(self, current_price: float, fiat_balance: float) -> float:
        """
        Calculate optimal position size based on volatility and risk management.
        """
        klines = self.klines(30)
        if not klines:
            return fiat_balance * 0.95  # Use 95% of balance as fallback

        volatility = self.calculate_volatility(klines)

        # Base position size on volatility (lower volatility = larger position)
        # Scale from 50% to 95% of balance based on volatility
        min_position_ratio = 0.5
        max_position_ratio = 0.95

        # Normalize volatility (typical crypto daily volatility: 0.01 to 0.1)
        normalized_volatility = min(1.0, max(0.0, (volatility - 0.01) / 0.09))

        # Inverse relationship: higher volatility = smaller position
        position_ratio = max_position_ratio - (
            normalized_volatility * (max_position_ratio - min_position_ratio)
        )

        return fiat_balance * position_ratio

    def buy(self) -> Order:
        """
        Places a buy order for the current client.

        :return Order: order
        """
        _price = self.suggested_buy_price()
        _fiat_balance = round(float(self.client.get_asset_balance(asset=self.fiat)["free"]), 2)

        # Minimum balance check
        min_notional = 10.0  # Minimum $10 order for most Binance pairs
        if _fiat_balance < min_notional:
            raise ValueError(
                f"Insufficient balance: ${_fiat_balance:.2f} < ${min_notional:.2f} minimum"
            )

        # Calculate optimal position size
        position_size = self.calculate_position_size(_price, _fiat_balance)
        _quantity = round(float(position_size / _price), 5)

        # Minimum quantity check
        if _quantity * _price < min_notional:
            raise ValueError(
                f"Order value too small: ${_quantity * _price:.2f} < ${min_notional:.2f} minimum"
            )

        # Reset trailing stop for new position
        self.last_high_price = None

        return Order(
            **self.client.create_order(
                symbol=self.symbol(),
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                price="%.2f" % _price,
                quantity="%.4f" % _quantity,
            )
        )

    def sell(self) -> Order:
        """
        Places a sell order for the current client.

        :return Order: order
        """
        _price = self.suggested_sell_price()
        _quantity = round(float(self.client.get_asset_balance(asset=self.crypto)["free"]), 5)

        # Minimum balance check
        min_notional = 10.0  # Minimum $10 order for most Binance pairs
        order_value = _quantity * _price

        if _quantity <= 0:
            raise ValueError(f"Insufficient {self.crypto} balance: {_quantity}")

        if order_value < min_notional:
            raise ValueError(
                f"Order value too small: ${order_value:.2f} < ${min_notional:.2f} minimum"
            )

        return Order(
            **self.client.create_order(
                symbol=self.symbol(),
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                price="%.2f" % _price,
                quantity="%.4f" % _quantity,
            )
        )

    def check_stop_loss(self):
        """
        Determines whether the client's stop loss has been reached.
        """
        last_order = self.orders[-1] if self.orders else None

        if last_order:
            last_order = Order(**last_order)

            if last_order.is_sell():
                stop_loss_price = float(last_order.price - (last_order.price * self.stop_loss))

                if float(self.price().get("askPrice")) < stop_loss_price:

                    self.client.cancel_order(symbol=self.symbol(), orderId=last_order.orderId)
