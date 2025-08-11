import os
import time

import requests
from binance.exceptions import BinanceAPIException
from services.logging import LoggingService
from services.market import Market
from services.wallet import Wallet


def analyze(m, w):
    """
    Analyzes the current market and wallet with enhanced indicators.
    :param m:
    :param w:
    """
    for k, v in w.balances().items():
        LoggingService.info("Balance {}: {:.8f}".format(k, v))

    for o in m.orders:
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

    # Get enhanced market analysis
    klines = m.klines(30)
    current_price = float(m.price().get("lastPrice", 0))

    if klines:
        rsi = m.calculate_rsi(klines)
        volatility = m.calculate_volatility(klines)
        trend = m.get_trend_direction()
        dynamic_buy, dynamic_sell = m.get_dynamic_thresholds()

        LoggingService.note("=== Enhanced Market Analysis ===")
        LoggingService.note(f"RSI: {rsi:.1f}" if rsi else "RSI: N/A")
        LoggingService.note(f"Trend: {trend.upper()}")
        LoggingService.note(f"Volatility: {volatility:.1%}")
        LoggingService.note(f"Dynamic Buy Threshold: {dynamic_buy:.1%}")
        LoggingService.note(f"Dynamic Sell Threshold: {dynamic_sell:.1%}")

    _sl = float(os.environ.get("BOT_SL", 0.03))
    LoggingService.note("Stop Loss: {:.1%}".format(_sl))
    LoggingService.note(f"Trailing Stop: {m.trailing_stop_percentage:.1%}")

    _p = m.price()
    LoggingService.note("Current {} Price: ${:.2f}".format(m.symbol(), float(_p["lastPrice"])))
    LoggingService.note("High {} Price: ${:.2f}".format(m.symbol(), float(_p["highPrice"])))
    LoggingService.note("Low {} Price: ${:.2f}".format(m.symbol(), float(_p["lowPrice"])))


def house_keeping():
    """
    Performs house-keeping tasks before starting the bot.
    """
    LoggingService.print_banner()

    if not os.environ.get("BINANCE_API_KEY", None):
        LoggingService.error("BINANCE_API_KEY not set, exiting.")
        exit(1)

    if not os.environ.get("BINANCE_API_SECRET", None):
        LoggingService.error("BINANCE_API_SECRET not set, exiting.")
        exit(1)


if __name__ == "__main__":
    house_keeping()

    market = Market()
    wallet = Wallet()

    market.sync()
    wallet.sync()

    analyze(market, wallet)

    while True:
        try:
            if wallet.has(market.fiat) and market.should_buy():
                try:
                    order = market.buy()

                    if order.orderId:
                        LoggingService.order(order, market)
                        market._record_successful_order()

                except BinanceAPIException as e:
                    LoggingService.error(f"Buy order failed: {e.message}")
                    market._record_failed_order()
                except ValueError as ve:
                    LoggingService.warn(f"Buy validation failed: {ve}")

            if wallet.has(market.crypto) and market.should_sell():
                try:
                    order = market.sell()

                    if order.orderId:
                        LoggingService.order(order, market)
                        market._record_successful_order()

                except BinanceAPIException as e:
                    LoggingService.error(f"Sell order failed: {e.message}")
                    market._record_failed_order()
                except ValueError as ve:
                    LoggingService.warn(f"Sell validation failed: {ve}")

            market.check_stop_loss()

            # Log circuit breaker status if active
            if market._is_circuit_breaker_active():
                remaining_time = market.circuit_breaker_timeout - (
                    time.time() - market.circuit_breaker_triggered_at
                )
                LoggingService.warn(
                    f"Circuit breaker active: {market.failed_orders_count} failures, {remaining_time/60:.1f}min remaining"
                )

            time.sleep(60)

            market.sync()
            wallet.sync()

        except KeyboardInterrupt as ke:
            LoggingService.warn("Bot stopped.")
            exit(0)
        except requests.exceptions.ConnectionError as ce:
            LoggingService.error(f"Connection error: {ce}")
            LoggingService.warn("Sleeping for 180s before restarting.")
            time.sleep(180)
            # Re-sync after network error
            try:
                market.sync()
                wallet.sync()
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
