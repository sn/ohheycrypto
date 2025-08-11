"""Command-line interface for OhHeyCrypto trading bot."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from ohheycrypto.__version__ import __version__
from ohheycrypto.bot import TradingBot
from ohheycrypto.config.settings import Config
from ohheycrypto.services.logging import LoggingService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_example_config(output_path: str) -> bool:
    """
    Create an example configuration file.

    Args:
        output_path: Path where to save the example config

    Returns:
        True if successful, False otherwise
    """
    example_config = {
        "binance": {"api_key": "YOUR_BINANCE_API_KEY", "api_secret": "YOUR_BINANCE_API_SECRET"},
        "trading": {
            "crypto": "BTC",
            "fiat": "USDT",
            "stop_loss": 3.0,
            "sell_threshold": 0.4,
            "buy_threshold": 0.2,
            "trailing_stop": 2.0,
            "position_sizing": {"min": 0.5, "max": 0.95},
        },
        "market_analysis": {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "ma_short": 10,
            "ma_long": 20,
            "volatility_lookback": 20,
        },
        "execution": {
            "check_interval": 60,
            "circuit_breaker": {"max_failures": 5, "cooldown": 3600},
            "min_order_value": 10.0,
        },
        "notifications": {"discord_webhook": ""},
    }

    try:
        output_file = Path(output_path)
        with open(output_file, "w") as f:
            json.dump(example_config, f, indent=2)
        print(f"Example configuration created at: {output_file}")
        print(
            "\nPlease edit this file and add your Binance API credentials before running the bot."
        )
        return True
    except Exception as e:
        print(f"Error creating example config: {e}")
        return False


def validate_config(config_path: str) -> bool:
    """
    Validate a configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        True if valid, False otherwise
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"Error: Configuration file not found: {config_path}")
            return False

        # Try to load and validate the config
        config = Config.load_from_file(config_file)

        # Check required fields
        issues = []

        if not config.api.binance_api_key or config.api.binance_api_key == "YOUR_BINANCE_API_KEY":
            issues.append("- Binance API key not configured")

        if (
            not config.api.binance_api_secret
            or config.api.binance_api_secret == "YOUR_BINANCE_API_SECRET"
        ):
            issues.append("- Binance API secret not configured")

        if config.trading.stop_loss <= 0:
            issues.append("- Stop loss must be greater than 0")

        if config.trading.stop_loss <= config.trading.sell_threshold:
            issues.append("- Stop loss must be greater than sell threshold")

        if config.trading.min_position_size > config.trading.max_position_size:
            issues.append("- Min position size cannot be greater than max position size")

        if config.execution.market_check_interval < 30:
            issues.append("- Market check interval should be at least 30 seconds")

        if issues:
            print("Configuration validation failed:")
            for issue in issues:
                print(issue)
            return False

        print("Configuration is valid!")
        print(f"\nTrading pair: {config.trading.crypto_currency}/{config.trading.fiat_currency}")
        print(f"Stop loss: {config.trading.stop_loss}%")
        print(f"Buy threshold: {config.trading.buy_threshold}%")
        print(f"Sell threshold: {config.trading.sell_threshold}%")
        print(f"Check interval: {config.execution.market_check_interval} seconds")

        if config.api.discord_webhook:
            print("Discord notifications: Enabled")
        else:
            print("Discord notifications: Disabled")

        return True

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"Error validating configuration: {e}")
        return False


def run_bot(config_path: str, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Run the trading bot.

    Args:
        config_path: Path to configuration file
        dry_run: If True, only validate and analyze without trading
        verbose: If True, enable verbose logging

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        config_file = Path(config_path)
        if not config_file.exists():
            LoggingService.error(f"Configuration file not found: {config_path}")
            print("\nTip: Run 'ohheycrypto init' to create an example configuration file.")
            return False

        # Load configuration
        config = Config.load_from_file(config_file)

        # Override with any environment variables
        env_config = Config.load_from_env()
        if env_config.api.binance_api_key:
            config.api.binance_api_key = env_config.api.binance_api_key
        if env_config.api.binance_api_secret:
            config.api.binance_api_secret = env_config.api.binance_api_secret

        # Create and run bot
        bot = TradingBot(config)

        if dry_run:
            LoggingService.print_banner()
            LoggingService.warn("DRY RUN MODE - No actual trades will be executed")

            if not bot.validate_environment():
                LoggingService.error("Configuration validation failed.")
                return False

            if not bot.initialize():
                LoggingService.error("Bot initialization failed.")
                return False

            # Just analyze and exit
            bot.analyze()
            LoggingService.success("Dry run completed successfully!")
            return True
        else:
            return bot.run()

    except KeyboardInterrupt:
        LoggingService.warn("Bot stopped by user.")
        return True
    except Exception as e:
        LoggingService.error(f"Failed to run bot: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ohheycrypto",
        description="OhHeyCrypto - Sophisticated cryptocurrency trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ohheycrypto init                    # Create example configuration file
  ohheycrypto validate config.json    # Validate configuration file
  ohheycrypto run config.json         # Run the trading bot
  ohheycrypto run config.json --dry   # Dry run (analysis only, no trades)
  
For more information, visit: https://github.com/sn/ohheycrypto
        """,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Create an example configuration file")
    init_parser.add_argument(
        "output",
        nargs="?",
        default="config.json",
        help="Output path for configuration file (default: config.json)",
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a configuration file")
    validate_parser.add_argument("config", help="Path to configuration file")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the trading bot")
    run_parser.add_argument("config", help="Path to configuration file")
    run_parser.add_argument(
        "--dry",
        "--dry-run",
        action="store_true",
        help="Perform dry run (analysis only, no actual trades)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    if args.command == "init":
        success = create_example_config(args.output)
        sys.exit(0 if success else 1)

    elif args.command == "validate":
        success = validate_config(args.config)
        sys.exit(0 if success else 1)

    elif args.command == "run":
        success = run_bot(args.config, dry_run=args.dry, verbose=args.verbose)
        sys.exit(0 if success else 1)

    else:
        # No command specified
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
