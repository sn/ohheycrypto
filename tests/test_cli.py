"""Tests for CLI functionality."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from ohheycrypto.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version_command(self):
        """Test --version command."""
        # Test using subprocess to simulate real CLI usage
        import subprocess

        result = subprocess.run(
            ["python", "-m", "ohheycrypto.cli", "--version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "ohheycrypto" in result.stdout.lower()

    def test_help_command(self):
        """Test --help command."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "ohheycrypto.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "OhHeyCrypto" in result.stdout
        assert "Sophisticated cryptocurrency trading bot" in result.stdout

    def test_init_command(self):
        """Test init command creates config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"

            import subprocess

            result = subprocess.run(
                ["python", "-m", "ohheycrypto.cli", "init", str(config_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0
            assert config_path.exists()

            # Verify the config file is valid JSON
            with open(config_path) as f:
                config_data = json.load(f)

            assert "binance" in config_data
            assert "trading" in config_data
            assert "market_analysis" in config_data
            assert "execution" in config_data
            assert "notifications" in config_data

    def test_validate_command_invalid_config(self):
        """Test validate command with invalid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid_config.json"

            # Create config with placeholder values
            config_data = {
                "binance": {
                    "api_key": "YOUR_BINANCE_API_KEY",
                    "api_secret": "YOUR_BINANCE_API_SECRET",
                },
                "trading": {"crypto": "BTC", "fiat": "USDT"},
            }

            with open(config_path, "w") as f:
                json.dump(config_data, f)

            import subprocess

            result = subprocess.run(
                ["python", "-m", "ohheycrypto.cli", "validate", str(config_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Should return non-zero exit code for invalid config
            assert result.returncode == 1
            assert (
                "API key not configured" in result.stdout
                or "API key not configured" in result.stderr
            )

    def test_validate_command_valid_config(self):
        """Test validate command with valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "valid_config.json"

            # Create config with valid (fake) values
            config_data = {
                "binance": {
                    "api_key": "valid_fake_api_key_12345",
                    "api_secret": "valid_fake_api_secret_12345",
                },
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

            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)

            import subprocess

            result = subprocess.run(
                ["python", "-m", "ohheycrypto.cli", "validate", str(config_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Should return zero exit code for valid config
            assert result.returncode == 0
            assert "Configuration is valid" in result.stdout

    def test_run_command_help(self):
        """Test run command help."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "ohheycrypto.cli", "run", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "run" in result.stdout.lower()
        assert "--dry" in result.stdout or "--dry-run" in result.stdout
