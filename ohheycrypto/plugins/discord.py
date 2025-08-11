import logging
import os
from typing import Any, Dict, Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from ohheycrypto.utils.retry import RetryConfig, retry_with_backoff

logger = logging.getLogger(__name__)


class DiscordService:
    def __init__(self):
        self.sl = 0
        self.st = 0
        self.bt = 0
        self.f = ""
        self.c = ""
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK")
        self._validate_webhook_url()

    def _validate_webhook_url(self):
        """Validate Discord webhook URL format."""
        if self.webhook_url and not self.webhook_url.startswith(
            "https://discord.com/api/webhooks/"
        ):
            logger.warning("Invalid Discord webhook URL format")

    @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=2.0))
    def post(
        self, channel_url: Optional[str], payload: Dict[str, Any]
    ) -> Optional[requests.Response]:
        """
        Posts a message to a Discord channel webhook

        https://birdie0.github.io/discord-webhooks-guide/discord_webhook.html

        Example:
        ```
            webhook_payload = {
            "username": "Any username",
            "content": "Message Content",
            "embeds": [
                {
                    "fields": [
                        {
                            "name": "From",
                            "value": "<any>"
                        },
                        {
                            "name": "Message",
                            "value": "<any>"
                        }
                    ]
                }
            ]}
        ```
        @param channel_url: The full url of the webhook to post to
        @param payload: The payload to send to the webhook
        @return: Response object if successful, None otherwise
        """
        if not channel_url:
            logger.debug("No Discord webhook URL configured, skipping notification")
            return None

        # Validate payload structure
        required_fields = ["username", "content", "embeds"]
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            logger.error(f"Discord payload missing required fields: {missing_fields}")
            return None

        try:
            resp = requests.post(channel_url, json=payload, timeout=10)

            if resp.ok:
                logger.debug("Discord notification sent successfully")
                return resp
            else:
                logger.error(f"Discord error: {resp.status_code} - {resp.text}")
                if resp.status_code >= 500:
                    raise RequestException(f"Discord server error: {resp.status_code}")
                return None

        except (ConnectionError, Timeout) as e:
            logger.error(f"Network error posting to Discord: {e}")
            raise
        except RequestException as e:
            logger.error(f"Discord webhook error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error posting to Discord: {e}")
            return None

    def sell(self, payload: Dict[str, Any]) -> None:
        """Send sell order notification to Discord."""
        if not self.webhook_url:
            return

        try:
            self.post(
                channel_url=self.webhook_url,
                payload={
                    "username": "Crypto Bot",
                    "content": "SELL order created",
                    "avatar_url": "https://i.imgur.com/Xp8gxVy.png",
                    "embeds": [
                        {
                            "fields": [
                                {"name": "Currency", "value": payload.get("symbol")},
                                {"name": "Price", "value": payload.get("price")},
                                {"name": "Quantity", "value": payload.get("origQty")},
                                {"name": "Type", "value": payload.get("type")},
                                {"name": "ID", "value": payload.get("orderId")},
                            ]
                        }
                    ],
                },
            )
        except Exception as e:
            logger.error(f"Failed to send sell notification to Discord: {e}")

    def buy(self, payload: Dict[str, Any]) -> None:
        """Send buy order notification to Discord."""
        if not self.webhook_url:
            return

        try:
            self.post(
                channel_url=self.webhook_url,
                payload={
                    "username": "Crypto Bot",
                    "content": "BUY order created",
                    "avatar_url": "https://i.imgur.com/Xp8gxVy.png",
                    "embeds": [
                        {
                            "fields": [
                                {"name": "Currency", "value": payload.get("symbol")},
                                {"name": "Price", "value": payload.get("price")},
                                {"name": "Quantity", "value": payload.get("origQty")},
                                {"name": "Type", "value": payload.get("type")},
                                {"name": "ID", "value": payload.get("orderId")},
                            ]
                        }
                    ],
                },
            )
        except Exception as e:
            logger.error(f"Failed to send buy notification to Discord: {e}")

    def botOnline(self) -> None:
        """Send bot online notification to Discord."""
        if not self.webhook_url:
            return

        try:
            self.post(
                channel_url=self.webhook_url,
                payload={
                    "username": "Crypto Bot",
                    "content": "Crypto Bot has come online",
                    "avatar_url": "https://i.imgur.com/Xp8gxVy.png",
                    "embeds": [
                        {
                            "fields": [
                                {"name": "Stop Loss", "value": "{:.4f}%".format(self.sl)},
                                {"name": "Sell Threshold", "value": "{:.4f}%".format(self.st)},
                                {"name": "Buy Threshold", "value": "{:.4f}%".format(self.bt)},
                                {"name": "Fiat", "value": self.f},
                                {"name": "Crypto", "value": self.c},
                            ]
                        }
                    ],
                },
            )
        except Exception as e:
            logger.error(f"Failed to send bot online notification to Discord: {e}")

    def setMarketValues(
        self, stop_loss: float, sell_threshold: float, buy_threshold: float, fiat: str, crypto: str
    ) -> None:
        """Set market values for bot online notification."""
        self.sl = stop_loss
        self.st = sell_threshold
        self.bt = buy_threshold
        self.f = fiat
        self.c = crypto
