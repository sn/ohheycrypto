from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Trade(BaseModel):
    """Model for storing trade history."""

    id: Optional[int] = Field(default=None, description="Database ID")
    order_id: int = Field(description="Binance order ID")
    symbol: str = Field(description="Trading pair (e.g., BTCUSDT)")
    side: OrderSide = Field(description="Buy or Sell")
    price: float = Field(description="Execution price")
    quantity: float = Field(description="Order quantity")
    value: float = Field(description="Total value (price * quantity)")
    fee: Optional[float] = Field(default=None, description="Trading fee")
    fee_asset: Optional[str] = Field(default=None, description="Fee currency")
    status: OrderStatus = Field(description="Order status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Trade timestamp")

    # Market conditions at time of trade
    rsi: Optional[float] = Field(default=None, description="RSI at trade time")
    volatility: Optional[float] = Field(default=None, description="Volatility at trade time")
    trend: Optional[str] = Field(default=None, description="Market trend at trade time")

    # Decision factors
    buy_threshold: Optional[float] = Field(default=None, description="Buy threshold used")
    sell_threshold: Optional[float] = Field(default=None, description="Sell threshold used")
    stop_loss: Optional[float] = Field(default=None, description="Stop loss percentage")

    # Performance tracking
    profit_loss: Optional[float] = Field(default=None, description="P&L for sell orders")
    profit_loss_percent: Optional[float] = Field(default=None, description="P&L percentage")
    holding_time_hours: Optional[float] = Field(default=None, description="Position holding time")

    class Config:
        orm_mode = True


class BotState(BaseModel):
    """Model for storing bot state."""

    id: int = Field(default=1, description="State ID (always 1 for single bot)")
    last_buy_price: Optional[float] = Field(default=None, description="Last buy price")
    last_buy_time: Optional[datetime] = Field(default=None, description="Last buy timestamp")
    last_sell_price: Optional[float] = Field(default=None, description="Last sell price")
    last_sell_time: Optional[datetime] = Field(default=None, description="Last sell timestamp")
    position_size: float = Field(default=0.0, description="Current position size")
    total_trades: int = Field(default=0, description="Total number of trades")
    successful_trades: int = Field(default=0, description="Number of profitable trades")
    total_profit_loss: float = Field(default=0.0, description="Cumulative P&L")
    circuit_breaker_active: bool = Field(default=False, description="Circuit breaker status")
    circuit_breaker_until: Optional[datetime] = Field(
        default=None, description="Circuit breaker end time"
    )
    failed_orders_count: int = Field(default=0, description="Consecutive failed orders")
    last_update: datetime = Field(default_factory=datetime.utcnow, description="Last state update")

    class Config:
        orm_mode = True


class MarketSnapshot(BaseModel):
    """Model for storing market snapshots."""

    id: Optional[int] = Field(default=None, description="Database ID")
    symbol: str = Field(description="Trading pair")
    price: float = Field(description="Current price")
    rsi: float = Field(description="RSI value")
    volatility: float = Field(description="Volatility")
    volume_24h: float = Field(description="24h volume")
    price_change_24h: float = Field(description="24h price change percentage")
    ma_short: float = Field(description="Short MA value")
    ma_long: float = Field(description="Long MA value")
    trend: str = Field(description="Market trend")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Snapshot timestamp")

    class Config:
        orm_mode = True


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit_loss: float = 0.0
    average_profit: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    average_holding_time_hours: float = 0.0
    best_trade_profit: float = 0.0
    worst_trade_loss: float = 0.0
    current_streak: int = 0
    max_winning_streak: int = 0
    max_losing_streak: int = 0
