from unittest.mock import MagicMock, Mock, patch

import pytest
from binance.exceptions import BinanceAPIException

from ohheycrypto.services.wallet import Wallet


class TestWallet:
    """Test cases for Wallet service."""

    @patch("ohheycrypto.services.wallet.Client")
    def test_wallet_initialization(self, mock_client_class, mock_binance_client):
        """Test wallet initialization with successful balance sync."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            assert wallet._balances == {"USDT": 1000.0, "BTC": 0.5}
            mock_binance_client.get_account.assert_called_once()

    @patch("ohheycrypto.services.wallet.Client")
    def test_wallet_initialization_failure(self, mock_client_class):
        """Test wallet initialization when API fails."""
        mock_client = Mock()
        mock_client.get_account.side_effect = BinanceAPIException(
            Mock(), 400, '{"code": -1000, "msg": "Unknown error"}'
        )
        mock_client_class.return_value = mock_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            # Should have empty balances on failure
            assert wallet._balances == {}

    @patch("ohheycrypto.services.wallet.Client")
    def test_sync_success(self, mock_client_class, mock_binance_client):
        """Test successful balance sync."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            # Update mock to return different balances
            mock_binance_client.get_account.return_value = {
                "balances": [
                    {"asset": "USDT", "free": "2000.0", "locked": "0.0"},
                    {"asset": "BTC", "free": "1.0", "locked": "0.0"},
                    {"asset": "ETH", "free": "5.0", "locked": "0.0"},
                ]
            }

            new_balances = wallet.sync()

            assert new_balances == {"USDT": 2000.0, "BTC": 1.0, "ETH": 5.0}
            assert wallet._balances == {"USDT": 2000.0, "BTC": 1.0, "ETH": 5.0}

    @patch("ohheycrypto.services.wallet.Client")
    def test_sync_with_retry(self, mock_client_class):
        """Test sync with retry on API failure."""
        mock_client = Mock()

        # Create a separate mock for initialization (succeeds)
        init_mock = Mock()
        init_mock.get_account.return_value = {"balances": []}

        # Create sync mock that fails first, then succeeds
        sync_mock = Mock()
        sync_mock.get_account.side_effect = [
            BinanceAPIException(Mock(), 429, '{"code": -1003, "msg": "Too many requests"}'),
            {
                "balances": [
                    {"asset": "USDT", "free": "1500.0", "locked": "0.0"},
                ]
            },
        ]

        mock_client_class.side_effect = [init_mock, sync_mock]

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()
            wallet._balances = {}  # Reset balances

            # Replace the client for sync operation
            wallet.client = sync_mock

            with patch("time.sleep"):  # Mock sleep to speed up test
                balances = wallet.sync()

            assert balances == {"USDT": 1500.0}
            assert sync_mock.get_account.call_count == 2

    @patch("ohheycrypto.services.wallet.Client")
    def test_has_balance(self, mock_client_class, mock_binance_client):
        """Test checking if wallet has balance for a symbol."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            assert wallet.has("USDT") is True
            assert wallet.has("BTC") is True
            assert wallet.has("ETH") is False
            assert wallet.has("DOGE") is False

    @patch("ohheycrypto.services.wallet.Client")
    def test_balance(self, mock_client_class, mock_binance_client):
        """Test getting balance for specific symbol."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            assert wallet.balance("USDT") == 1000.0
            assert wallet.balance("BTC") == 0.5
            assert wallet.balance("ETH") == 0
            assert wallet.balance("INVALID") == 0

    @patch("ohheycrypto.services.wallet.Client")
    def test_balances(self, mock_client_class, mock_binance_client):
        """Test getting all balances."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            balances = wallet.balances()
            assert balances == {"USDT": 1000.0, "BTC": 0.5}

            # Ensure it returns a copy
            balances["USDT"] = 0
            assert wallet._balances["USDT"] == 1000.0

    @patch("ohheycrypto.services.wallet.Client")
    def test_refresh_balances(self, mock_client_class, mock_binance_client):
        """Test force refresh of balances."""
        mock_client_class.return_value = mock_binance_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()

            # Change mock response
            mock_binance_client.get_account.return_value = {
                "balances": [
                    {"asset": "USDT", "free": "3000.0", "locked": "0.0"},
                ]
            }

            refreshed = wallet.refresh_balances()
            assert refreshed == {"USDT": 3000.0}
            assert wallet._balances == {"USDT": 3000.0}

    @patch("ohheycrypto.services.wallet.Client")
    def test_refresh_balances_failure(self, mock_client_class):
        """Test refresh balances when API fails."""
        mock_client = Mock()
        mock_client.get_account.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client

        with patch.dict(
            "os.environ", {"BINANCE_API_KEY": "test_key", "BINANCE_API_SECRET": "test_secret"}
        ):
            wallet = Wallet()
            wallet._balances = {"USDT": 1000.0}  # Set initial balance

            refreshed = wallet.refresh_balances()
            assert refreshed is None
            assert wallet._balances == {"USDT": 1000.0}  # Should keep old balances
