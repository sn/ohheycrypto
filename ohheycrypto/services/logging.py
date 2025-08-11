from datetime import datetime
from typing import TYPE_CHECKING

from yachalk import chalk

from ohheycrypto.models.order import Order

if TYPE_CHECKING:
    from ohheycrypto.services.market import Market


class LoggingService:
    @staticmethod
    def order(order: Order, market: "Market"):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_value = order.price * order.origQty

        # Log structured order data
        print(
            chalk.white(current_time),
            chalk.white("-"),
            chalk.green("ORDER PLACED:"),
            chalk.yellow(f"ID#{order.orderId}"),
            chalk.white(f"{order.side.upper()} {order.symbol}"),
            chalk.white(f"@ ${order.price:.2f}"),
            chalk.white(f"qty: {order.origQty:.4f}"),
            chalk.green(f"value: ${order_value:.2f}"),
        )

        # Log enhanced market conditions
        current_price = float(market.price().get("askPrice", 0))
        price_diff = (
            ((order.price - current_price) / current_price) * 100 if current_price > 0 else 0
        )

        # Get additional market data
        klines = market.klines(30)
        rsi = market.calculate_rsi(klines) if klines else None
        trend = market.get_trend_direction() if klines else "unknown"

        print(
            chalk.white(current_time),
            chalk.white("-"),
            chalk.blue("MARKET:"),
            chalk.white(f"current: ${current_price:.2f}"),
            chalk.white(f"diff: {price_diff:+.2f}%"),
            chalk.cyan(f"RSI: {rsi:.0f}" if rsi else "RSI: N/A"),
            chalk.cyan(f"trend: {trend.upper()}"),
        )

        print(
            chalk.white(current_time),
            chalk.white("-"),
            chalk.blue("THRESHOLDS:"),
            chalk.white(f"SL: {market.stop_loss:.1%}"),
            chalk.white(f"ST: {market.sell_threshold:.1%}"),
            chalk.white(f"BT: {market.buy_threshold:.1%}"),
            chalk.white(f"TS: {market.trailing_stop_percentage:.1%}"),
        )

    @staticmethod
    def print_banner():
        print("\n")
        print(chalk.magenta_bright("───╔╗─╔╗────────────────────╔╗"))
        print(chalk.magenta_bright("───║║─║║───────────────────╔╝╚╗"))
        print(chalk.magenta_bright("╔══╣╚═╣╚═╦══╦╗─╔╦══╦═╦╗─╔╦═╩╗╔╬══╗"))
        print(chalk.blue_bright("║╔╗║╔╗║╔╗║║═╣║─║║╔═╣╔╣║─║║╔╗║║║╔╗║"))
        print(chalk.blue_bright("║╚╝║║║║║║║║═╣╚═╝║╚═╣║║╚═╝║╚╝║╚╣╚╝║"))
        print(chalk.green_bright("╚══╩╝╚╩╝╚╩══╩═╗╔╩══╩╝╚═╗╔╣╔═╩═╩══╝"))
        print(chalk.green_bright("────────────╔═╝║─────╔═╝║║║"))
        print(chalk.green_bright("────────────╚══╝─────╚══╝╚╝"))
        print("Trading Bot v0.2.0")
        print("https://github.com/sn/ohheycrypto")
        print("\n")

        LoggingService.success("Bot started.")
        LoggingService.note("Press CTRL+C to exit.")

    @staticmethod
    def note(msg: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(chalk.white(current_time), chalk.white("-"), chalk.white(msg))

    @staticmethod
    def info(msg: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(chalk.white(current_time), chalk.white("-"), chalk.magenta_bright(msg))

    @staticmethod
    def warn(msg: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(chalk.white(current_time), chalk.white("-"), chalk.yellow(msg))

    @staticmethod
    def success(msg: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(chalk.white(current_time), chalk.white("-"), chalk.green(msg))

    @staticmethod
    def error(msg: str):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(chalk.white(current_time), chalk.white("-"), chalk.red(msg))
