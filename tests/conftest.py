import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_binance_client():
    """Mock Binance client for testing."""
    client = Mock()

    # Mock account info
    client.get_account.return_value = {
        "balances": [
            {"asset": "USDT", "free": "1000.0", "locked": "0.0"},
            {"asset": "BTC", "free": "0.5", "locked": "0.0"},
        ]
    }

    # Mock ticker info
    client.get_ticker.return_value = {
        "symbol": "BTCUSDT",
        "priceChange": "100.0",
        "priceChangePercent": "1.5",
        "lastPrice": "50000.0",
        "volume": "1000.0",
        "count": 10000,
    }

    # Mock klines (candlestick) data
    client.get_klines.return_value = [
        [
            1640995200000,
            "48000",
            "48500",
            "47800",
            "48200",
            "100",
            1640998800000,
            "4820000",
            100,
            "50",
            "2410000",
            "0",
        ],
        [
            1640998800000,
            "48200",
            "48700",
            "48000",
            "48500",
            "110",
            1641002400000,
            "5335000",
            110,
            "55",
            "2667500",
            "0",
        ],
    ]

    # Mock order creation
    client.create_order.return_value = {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "price": "50000",
        "origQty": "0.01",
        "type": "MARKET",
        "side": "BUY",
        "status": "FILLED",
    }

    return client


@pytest.fixture
def mock_discord_service():
    """Mock Discord service for testing."""
    service = Mock()
    service.webhook_url = "https://discord.com/api/webhooks/test"
    service.post.return_value = Mock(ok=True)
    return service


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from ohheycrypto.config.settings import (
        APIConfig,
        Config,
        ExecutionConfig,
        MarketAnalysisConfig,
        TradingConfig,
    )

    return Config(
        trading=TradingConfig(
            stop_loss=3.0, sell_threshold=0.4, buy_threshold=0.2, fiat="USDT", crypto="BTC"
        ),
        market_analysis=MarketAnalysisConfig(
            rsi_period=14, rsi_oversold=30.0, rsi_overbought=70.0, ma_short=10, ma_long=20
        ),
        execution=ExecutionConfig(
            check_interval=60, circuit_breaker={"max_failures": 5, "cooldown": 3600}
        ),
        api=APIConfig(
            binance_api_key="test_key",
            binance_api_secret="test_secret",
            discord_webhook="https://discord.com/api/webhooks/test",
        ),
    )


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "prices": [48000, 48200, 48500, 48300, 48600, 48400, 48700, 48900, 49000, 49200],
        "volumes": [100, 110, 105, 115, 120, 108, 125, 130, 135, 140],
        "rsi": 45.5,
        "volatility": 0.02,
        "trend": "neutral",
        "ma_short": 48600,
        "ma_long": 48400,
    }
