from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from ohheycrypto.plugins.discord import DiscordService


class TestDiscordService:
    """Test cases for Discord service."""

    def test_discord_initialization_with_webhook(self):
        """Test Discord service initialization with valid webhook."""
        with patch.dict(
            "os.environ", {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/123/abc"}
        ):
            service = DiscordService()
            assert service.webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_discord_initialization_without_webhook(self):
        """Test Discord service initialization without webhook."""
        with patch.dict("os.environ", {}, clear=True):
            service = DiscordService()
            assert service.webhook_url is None

    def test_discord_initialization_invalid_webhook(self):
        """Test Discord service initialization with invalid webhook URL."""
        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://invalid-webhook.com/webhook"}):
            with patch("ohheycrypto.plugins.discord.logger") as mock_logger:
                service = DiscordService()
                mock_logger.warning.assert_called_with("Invalid Discord webhook URL format")

    @patch("requests.post")
    def test_post_success(self, mock_post):
        """Test successful Discord post."""
        mock_response = Mock()
        mock_response.ok = True
        mock_post.return_value = mock_response

        service = DiscordService()
        payload = {"username": "Test Bot", "content": "Test message", "embeds": []}

        result = service.post("https://discord.com/api/webhooks/test", payload)

        assert result == mock_response
        mock_post.assert_called_once_with(
            "https://discord.com/api/webhooks/test", json=payload, timeout=10
        )

    def test_post_no_url(self):
        """Test post with no webhook URL."""
        service = DiscordService()
        payload = {"username": "Test Bot", "content": "Test message", "embeds": []}

        result = service.post(None, payload)
        assert result is None

    def test_post_missing_fields(self):
        """Test post with missing required fields."""
        service = DiscordService()
        payload = {
            "username": "Test Bot"
            # Missing content and embeds
        }

        with patch("ohheycrypto.plugins.discord.logger") as mock_logger:
            result = service.post("https://discord.com/api/webhooks/test", payload)
            assert result is None
            mock_logger.error.assert_called()

    @patch("requests.post")
    def test_post_rate_limited(self, mock_post):
        """Test post when rate limited."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}
        mock_post.return_value = mock_response

        service = DiscordService()
        payload = {"username": "Test Bot", "content": "Test message", "embeds": []}

        result = service.post("https://discord.com/api/webhooks/test", payload)
        assert result is None  # Should return None for client errors like 429

    @patch("requests.post")
    def test_post_webhook_not_found(self, mock_post):
        """Test post when webhook not found."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        service = DiscordService()
        payload = {"username": "Test Bot", "content": "Test message", "embeds": []}

        result = service.post("https://discord.com/api/webhooks/test", payload)
        assert result is None

    @patch("requests.post")
    def test_post_with_retry(self, mock_post):
        """Test post with retry on network error."""
        # First call fails with timeout, second succeeds
        mock_response = Mock()
        mock_response.ok = True
        mock_post.side_effect = [Timeout("Connection timeout"), mock_response]

        service = DiscordService()
        payload = {"username": "Test Bot", "content": "Test message", "embeds": []}

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = service.post("https://discord.com/api/webhooks/test", payload)

        assert result == mock_response
        assert mock_post.call_count == 2

    @patch("ohheycrypto.plugins.discord.DiscordService.post")
    def test_sell_notification(self, mock_post):
        """Test sell order notification."""
        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/test"}):
            service = DiscordService()

            order_data = {
                "symbol": "BTCUSDT",
                "price": "50000",
                "origQty": "0.01",
                "type": "MARKET",
                "orderId": 12345,
            }

            service.sell(order_data)

            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args["channel_url"] == "https://discord.com/api/webhooks/test"
            assert call_args["payload"]["content"] == "SELL order created"

    @patch("ohheycrypto.plugins.discord.DiscordService.post")
    def test_buy_notification(self, mock_post):
        """Test buy order notification."""
        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/test"}):
            service = DiscordService()

            order_data = {
                "symbol": "BTCUSDT",
                "price": "45000",
                "origQty": "0.02",
                "type": "MARKET",
                "orderId": 12346,
            }

            service.buy(order_data)

            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args["channel_url"] == "https://discord.com/api/webhooks/test"
            assert call_args["payload"]["content"] == "BUY order created"

    @patch("ohheycrypto.plugins.discord.DiscordService.post")
    def test_bot_online_notification(self, mock_post):
        """Test bot online notification."""
        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/test"}):
            service = DiscordService()
            service.setMarketValues(3.0, 0.4, 0.2, "USDT", "BTC")

            service.botOnline()

            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            payload = call_args["payload"]
            assert payload["content"] == "Crypto Bot has come online"

            # Check market values in embed
            fields = payload["embeds"][0]["fields"]
            assert any(f["name"] == "Stop Loss" and "3.0000%" in f["value"] for f in fields)
            assert any(f["name"] == "Fiat" and f["value"] == "USDT" for f in fields)
            assert any(f["name"] == "Crypto" and f["value"] == "BTC" for f in fields)

    def test_notification_without_webhook(self):
        """Test notifications when no webhook is configured."""
        with patch.dict("os.environ", {}, clear=True):
            service = DiscordService()

            # These should not raise exceptions
            service.sell({"symbol": "BTCUSDT"})
            service.buy({"symbol": "BTCUSDT"})
            service.botOnline()

    @patch("ohheycrypto.plugins.discord.DiscordService.post")
    def test_notification_error_handling(self, mock_post):
        """Test error handling in notifications."""
        mock_post.side_effect = Exception("Network error")

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/test"}):
            service = DiscordService()

            # Should not raise exception
            service.sell({"symbol": "BTCUSDT"})
            service.buy({"symbol": "BTCUSDT"})
            service.botOnline()
