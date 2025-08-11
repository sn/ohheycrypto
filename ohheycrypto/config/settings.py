import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class PositionSizing(BaseModel):
    """Position sizing configuration."""

    min: float = Field(
        default=0.5, ge=0.1, le=1.0, description="Minimum position size as fraction of balance"
    )
    max: float = Field(
        default=0.95, ge=0.1, le=1.0, description="Maximum position size as fraction of balance"
    )


class TradingConfig(BaseModel):
    """Trading parameters configuration."""

    crypto: str = Field(default="BTC", description="Cryptocurrency to trade")
    fiat: str = Field(default="USDT", description="Fiat currency for trading")
    stop_loss: float = Field(default=3.0, ge=0.1, le=20.0, description="Stop loss percentage")
    sell_threshold: float = Field(
        default=0.4, ge=0.1, le=5.0, description="Sell threshold percentage"
    )
    buy_threshold: float = Field(
        default=0.2, ge=0.1, le=5.0, description="Buy threshold percentage"
    )
    trailing_stop: float = Field(
        default=2.0, ge=0.5, le=10.0, description="Trailing stop percentage"
    )
    position_sizing: PositionSizing = Field(
        default_factory=PositionSizing, description="Position sizing config"
    )

    # Legacy field mappings for backward compatibility
    @property
    def fiat_currency(self) -> str:
        return self.fiat

    @property
    def crypto_currency(self) -> str:
        return self.crypto

    @property
    def min_position_size(self) -> float:
        return self.position_sizing.min

    @property
    def max_position_size(self) -> float:
        return self.position_sizing.max

    @property
    def trailing_stop_percentage(self) -> float:
        return self.trailing_stop

    @field_validator("position_sizing")
    @classmethod
    def validate_position_sizing(cls, v):
        if v.max < v.min:
            raise ValueError("max position size must be >= min position size")
        return v


class MarketAnalysisConfig(BaseModel):
    """Market analysis parameters."""

    rsi_period: int = Field(default=14, ge=5, le=50, description="RSI calculation period")
    rsi_oversold: float = Field(
        default=30.0, ge=10.0, le=40.0, description="RSI oversold threshold"
    )
    rsi_overbought: float = Field(
        default=70.0, ge=60.0, le=90.0, description="RSI overbought threshold"
    )
    ma_short: int = Field(default=10, ge=5, le=50, description="Short moving average period")
    ma_long: int = Field(default=20, ge=10, le=100, description="Long moving average period")
    volatility_lookback: int = Field(
        default=20, ge=10, le=50, description="Volatility calculation lookback period"
    )

    # Legacy field mappings
    @property
    def ma_short_period(self) -> int:
        return self.ma_short

    @property
    def ma_long_period(self) -> int:
        return self.ma_long

    @field_validator("ma_long")
    @classmethod
    def validate_ma_periods(cls, v, info):
        if hasattr(info, "data") and "ma_short" in info.data and v <= info.data["ma_short"]:
            raise ValueError("ma_long must be > ma_short")
        return v


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    max_failures: int = Field(
        default=5, ge=3, le=10, description="Failed orders before circuit breaker"
    )
    cooldown: int = Field(
        default=3600, ge=600, le=7200, description="Circuit breaker cooldown in seconds"
    )


class ExecutionConfig(BaseModel):
    """Execution and timing configuration."""

    check_interval: int = Field(
        default=60, ge=30, le=300, description="Market check interval in seconds"
    )
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    min_order_value: float = Field(
        default=10.0, ge=5.0, le=50.0, description="Minimum order value in fiat"
    )
    order_timeout: int = Field(
        default=30, ge=10, le=60, description="Order execution timeout in seconds"
    )

    # Legacy field mappings
    @property
    def market_check_interval(self) -> int:
        return self.check_interval

    @property
    def circuit_breaker_threshold(self) -> int:
        return self.circuit_breaker.max_failures

    @property
    def circuit_breaker_cooldown(self) -> int:
        return self.circuit_breaker.cooldown

    @property
    def min_notional_value(self) -> float:
        return self.min_order_value


class BinanceConfig(BaseModel):
    """Binance API configuration."""

    api_key: Optional[str] = Field(default=None, description="Binance API key")
    api_secret: Optional[str] = Field(default=None, description="Binance API secret")


class NotificationsConfig(BaseModel):
    """Notifications configuration."""

    discord_webhook: Optional[str] = Field(default=None, description="Discord webhook URL")


class APIConfig(BaseModel):
    """API configuration - legacy wrapper."""

    binance_api_key: Optional[str] = Field(default=None, description="Binance API key")
    binance_api_secret: Optional[str] = Field(default=None, description="Binance API secret")
    discord_webhook: Optional[str] = Field(default=None, description="Discord webhook URL")

    @field_validator("binance_api_key")
    @classmethod
    def validate_api_key(cls, v):
        if v and len(v) < 10:
            raise ValueError("binance_api_key appears to be invalid")
        return v

    @field_validator("binance_api_secret")
    @classmethod
    def validate_api_secret(cls, v):
        if v and len(v) < 10:
            raise ValueError("binance_api_secret appears to be invalid")
        return v

    @field_validator("discord_webhook")
    @classmethod
    def validate_discord_webhook(cls, v):
        if v and not v.startswith("https://discord.com/api/webhooks/"):
            raise ValueError("Invalid Discord webhook URL format")
        return v


class Config(BaseModel):
    """Main configuration class."""

    binance: Optional[BinanceConfig] = Field(default=None)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    market_analysis: MarketAnalysisConfig = Field(default_factory=MarketAnalysisConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    notifications: Optional[NotificationsConfig] = Field(default=None)

    # Legacy API config for backward compatibility
    api: APIConfig = Field(default_factory=APIConfig)

    def __init__(self, **data):
        super().__init__(**data)
        if self.binance:
            self.api.binance_api_key = self.binance.api_key
            self.api.binance_api_secret = self.binance.api_secret
        if self.notifications:
            self.api.discord_webhook = self.notifications.discord_webhook

    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """Load configuration from JSON file."""
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = json.load(f)
                return cls(**data)
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return cls()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return cls()
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            return cls()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return cls()

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Override with environment variables
        env_mappings = {
            "BOT_SL": ("trading", "stop_loss", lambda x: float(x) * 100),  # Convert to percentage
            "BOT_ST": ("trading", "sell_threshold", lambda x: float(x) * 100),
            "BOT_BT": ("trading", "buy_threshold", lambda x: float(x) * 100),
            "BOT_FIAT": ("trading", "fiat", str),
            "BOT_CRYPTO": ("trading", "crypto", str),
            "BINANCE_API_KEY": ("api", "binance_api_key", str),
            "BINANCE_API_SECRET": ("api", "binance_api_secret", str),
            "DISCORD_WEBHOOK": ("api", "discord_webhook", str),
        }

        for env_var, (section, field, type_func) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                try:
                    typed_value = type_func(value)
                    setattr(getattr(config, section), field, typed_value)
                except (ValueError, ValidationError) as e:
                    logger.error(f"Invalid value for {env_var}: {e}")

        return config

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        try:
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(self.model_dump(), f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def validate_for_trading(self) -> bool:
        """Validate that configuration is complete for trading."""
        if not self.api.binance_api_key or not self.api.binance_api_secret:
            logger.error("Binance API credentials not configured")
            return False
        return True


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the configuration singleton."""
    global _config
    if _config is None:
        config_path = Path("config.json")
        if config_path.exists():
            _config = Config.load_from_file(config_path)
        else:
            _config = Config()

        # Override with environment variables
        env_config = Config.load_from_env()
        _config.api = env_config.api

        # Override trading params if set in env
        if os.environ.get("BOT_SL"):
            _config.trading.stop_loss = env_config.trading.stop_loss
        if os.environ.get("BOT_ST"):
            _config.trading.sell_threshold = env_config.trading.sell_threshold
        if os.environ.get("BOT_BT"):
            _config.trading.buy_threshold = env_config.trading.buy_threshold
        if os.environ.get("BOT_FIAT"):
            _config.trading.fiat = env_config.trading.fiat
        if os.environ.get("BOT_CRYPTO"):
            _config.trading.crypto = env_config.trading.crypto

    return _config


def reload_config() -> Config:
    """Force reload configuration."""
    global _config
    _config = None
    return get_config()
