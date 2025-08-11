import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from pydantic import ValidationError

from ohheycrypto.config.settings import (
    Config, TradingConfig, MarketAnalysisConfig, 
    ExecutionConfig, APIConfig, get_config, reload_config
)


class TestTradingConfig:
    """Test trading configuration validation."""
    
    def test_default_values(self):
        """Test default trading config values."""
        config = TradingConfig()
        assert config.stop_loss == 3.0
        assert config.sell_threshold == 0.4
        assert config.buy_threshold == 0.2
        assert config.fiat_currency == "USDT"
        assert config.crypto_currency == "BTC"
    
    def test_validation_boundaries(self):
        """Test validation of boundary values."""
        # Valid config
        config = TradingConfig(
            stop_loss=10.0,
            sell_threshold=2.5,
            buy_threshold=1.0,
            min_position_size=0.3,
            max_position_size=0.8
        )
        assert config.stop_loss == 10.0
        
        # Invalid stop loss
        with pytest.raises(ValidationError):
            TradingConfig(stop_loss=25.0)  # > 20.0
        
        with pytest.raises(ValidationError):
            TradingConfig(stop_loss=0.05)  # < 0.1
    
    def test_position_size_validation(self):
        """Test position size validation."""
        # Valid
        config = TradingConfig(
            position_sizing={"min": 0.3, "max": 0.7}
        )
        assert config.min_position_size == 0.3
        assert config.max_position_size == 0.7
        
        # Invalid - max < min
        with pytest.raises(ValidationError):
            TradingConfig(
                position_sizing={"min": 0.7, "max": 0.3}
            )


class TestMarketAnalysisConfig:
    """Test market analysis configuration."""
    
    def test_default_values(self):
        """Test default market analysis values."""
        config = MarketAnalysisConfig()
        assert config.rsi_period == 14
        assert config.rsi_oversold == 30.0
        assert config.rsi_overbought == 70.0
        assert config.ma_short_period == 10
        assert config.ma_long_period == 20
    
    def test_ma_period_validation(self):
        """Test moving average period validation."""
        # Valid
        config = MarketAnalysisConfig(ma_short=15, ma_long=30)
        assert config.ma_short_period == 15
        assert config.ma_long_period == 30
        
        # Invalid - long <= short
        with pytest.raises(ValidationError):
            MarketAnalysisConfig(ma_short=20, ma_long=20)
        
        with pytest.raises(ValidationError):
            MarketAnalysisConfig(ma_short=25, ma_long=20)


class TestAPIConfig:
    """Test API configuration."""
    
    def test_api_key_validation(self):
        """Test API key validation."""
        # Valid
        config = APIConfig(
            binance_api_key="valid_api_key_12345",
            binance_api_secret="valid_secret_12345"
        )
        assert config.binance_api_key == "valid_api_key_12345"
        
        # Invalid - too short
        with pytest.raises(ValidationError):
            APIConfig(binance_api_key="short")
    
    def test_discord_webhook_validation(self):
        """Test Discord webhook validation."""
        # Valid
        config = APIConfig(
            discord_webhook="https://discord.com/api/webhooks/123/abc"
        )
        assert config.discord_webhook == "https://discord.com/api/webhooks/123/abc"
        
        # Invalid format
        with pytest.raises(ValidationError):
            APIConfig(discord_webhook="https://invalid.com/webhook")


class TestConfig:
    """Test main configuration class."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()
        assert isinstance(config.trading, TradingConfig)
        assert isinstance(config.market_analysis, MarketAnalysisConfig)
        assert isinstance(config.execution, ExecutionConfig)
        assert isinstance(config.api, APIConfig)
    
    def test_load_from_file(self, tmp_path):
        """Test loading configuration from file."""
        config_data = {
            "trading": {
                "stop_loss": 5.0,
                "sell_threshold": 0.5
            },
            "market_analysis": {
                "rsi_period": 20
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Config.load_from_file(config_file)
        assert config.trading.stop_loss == 5.0
        assert config.trading.sell_threshold == 0.5
        assert config.market_analysis.rsi_period == 20
        assert config.trading.buy_threshold == 0.2  # Default value
    
    def test_load_from_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file returns defaults."""
        config_file = tmp_path / "nonexistent.json"
        
        with patch('ohheycrypto.config.settings.logger') as mock_logger:
            config = Config.load_from_file(config_file)
            mock_logger.warning.assert_called()
        
        assert config.trading.stop_loss == 3.0  # Default
    
    def test_load_from_invalid_json(self, tmp_path):
        """Test loading from invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("invalid json{")
        
        with patch('ohheycrypto.config.settings.logger') as mock_logger:
            config = Config.load_from_file(config_file)
            mock_logger.error.assert_called()
        
        assert config.trading.stop_loss == 3.0  # Default
    
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        with patch.dict('os.environ', {
            'BOT_SL': '0.075',  # Decimal format (7.5% as 0.075)
            'BOT_ST': '0.008',  # Decimal format (0.8% as 0.008) 
            'BOT_BT': '0.003',  # Decimal format (0.3% as 0.003)
            'BOT_FIAT': 'BUSD',
            'BOT_CRYPTO': 'ETH',
            'BINANCE_API_KEY': 'test_api_key_123',
            'BINANCE_API_SECRET': 'test_secret_123',
            'DISCORD_WEBHOOK': 'https://discord.com/api/webhooks/test'
        }):
            config = Config.load_from_env()
            
            assert config.trading.stop_loss == 7.5  # Converted to percentage
            assert config.trading.sell_threshold == 0.8  # Converted to percentage
            assert config.trading.buy_threshold == 0.3  # Converted to percentage
            assert config.trading.fiat_currency == 'BUSD'
            assert config.trading.crypto_currency == 'ETH'
            assert config.api.binance_api_key == 'test_api_key_123'
            assert config.api.binance_api_secret == 'test_secret_123'
            assert config.api.discord_webhook == 'https://discord.com/api/webhooks/test'
    
    def test_save_to_file(self, tmp_path):
        """Test saving configuration to file."""
        config = Config()
        config.trading.stop_loss = 4.5
        
        config_file = tmp_path / "saved_config.json"
        config.save_to_file(config_file)
        
        assert config_file.exists()
        
        # Load and verify
        with open(config_file) as f:
            loaded_data = json.load(f)
        assert loaded_data['trading']['stop_loss'] == 4.5
    
    def test_validate_for_trading(self):
        """Test validation for trading readiness."""
        # Without API credentials
        config = Config()
        assert config.validate_for_trading() is False
        
        # With API credentials
        config.api.binance_api_key = "test_key"
        config.api.binance_api_secret = "test_secret"
        assert config.validate_for_trading() is True


class TestConfigSingleton:
    """Test configuration singleton behavior."""
    
    @patch('ohheycrypto.config.settings._config', None)
    def test_get_config_singleton(self):
        """Test get_config returns singleton."""
        with patch.dict('os.environ', {
            'BINANCE_API_KEY': 'test_key',
            'BINANCE_API_SECRET': 'test_secret'
        }):
            config1 = get_config()
            config2 = get_config()
            
            assert config1 is config2
    
    @patch('ohheycrypto.config.settings._config', None)
    def test_reload_config(self):
        """Test reload_config forces new instance."""
        with patch.dict('os.environ', {
            'BINANCE_API_KEY': 'test_key',
            'BINANCE_API_SECRET': 'test_secret'
        }):
            config1 = get_config()
            config2 = reload_config()
            config3 = get_config()
            
            assert config1 is not config2
            assert config2 is config3
    
    @patch('ohheycrypto.config.settings._config', None)
    def test_config_with_file_and_env(self, tmp_path):
        """Test config loading with both file and env vars."""
        # Create config file
        config_data = {
            "trading": {
                "stop_loss": 5.0,
                "sell_threshold": 0.5
            }
        }
        
        config_file = Path("config.json")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(config_data))), \
             patch.dict('os.environ', {
                 'BOT_ST': '0.009',  # Override file value (0.9% as decimal)
                 'BINANCE_API_KEY': 'env_key',
                 'BINANCE_API_SECRET': 'env_secret'
             }):
            
            config = get_config()
            
            # File value
            assert config.trading.stop_loss == 5.0
            # Env override (check for floating point precision)
            assert abs(config.trading.sell_threshold - 0.9) < 0.0001
            # Env value
            assert config.api.binance_api_key == 'env_key'