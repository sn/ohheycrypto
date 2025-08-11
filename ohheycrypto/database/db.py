import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ohheycrypto.database.models import (
    BotState,
    MarketSnapshot,
    OrderSide,
    PerformanceMetrics,
    Trade,
)

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for trade history and bot state."""

    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Trades table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    value REAL NOT NULL,
                    fee REAL,
                    fee_asset TEXT,
                    status TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    rsi REAL,
                    volatility REAL,
                    trend TEXT,
                    buy_threshold REAL,
                    sell_threshold REAL,
                    stop_loss REAL,
                    profit_loss REAL,
                    profit_loss_percent REAL,
                    holding_time_hours REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Bot state table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_state (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    last_buy_price REAL,
                    last_buy_time TIMESTAMP,
                    last_sell_price REAL,
                    last_sell_time TIMESTAMP,
                    position_size REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    total_profit_loss REAL DEFAULT 0,
                    circuit_breaker_active BOOLEAN DEFAULT 0,
                    circuit_breaker_until TIMESTAMP,
                    failed_orders_count INTEGER DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (id = 1)
                )
            """
            )

            # Market snapshots table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    rsi REAL NOT NULL,
                    volatility REAL NOT NULL,
                    volume_24h REAL NOT NULL,
                    price_change_24h REAL NOT NULL,
                    ma_short REAL NOT NULL,
                    ma_long REAL NOT NULL,
                    trend TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON market_snapshots(timestamp)"
            )

            # Initialize bot state if not exists
            cursor.execute("INSERT OR IGNORE INTO bot_state (id) VALUES (1)")

            logger.info("Database initialized successfully")

    def save_trade(self, trade: Trade) -> int:
        """Save a trade to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO trades (
                    order_id, symbol, side, price, quantity, value,
                    fee, fee_asset, status, timestamp,
                    rsi, volatility, trend,
                    buy_threshold, sell_threshold, stop_loss,
                    profit_loss, profit_loss_percent, holding_time_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trade.order_id,
                    trade.symbol,
                    trade.side,
                    trade.price,
                    trade.quantity,
                    trade.value,
                    trade.fee,
                    trade.fee_asset,
                    trade.status,
                    trade.timestamp,
                    trade.rsi,
                    trade.volatility,
                    trade.trend,
                    trade.buy_threshold,
                    trade.sell_threshold,
                    trade.stop_loss,
                    trade.profit_loss,
                    trade.profit_loss_percent,
                    trade.holding_time_hours,
                ),
            )

            trade_id = cursor.lastrowid
            logger.info(f"Saved trade {trade.order_id} to database (ID: {trade_id})")
            return trade_id

    def get_last_buy_trade(self, symbol: str) -> Optional[Trade]:
        """Get the last buy trade for a symbol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM trades
                WHERE symbol = ? AND side = 'BUY' AND status = 'FILLED'
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (symbol,),
            )

            row = cursor.fetchone()
            if row:
                return Trade(**dict(row))
            return None

    def get_trades(
        self,
        symbol: Optional[str] = None,
        side: Optional[OrderSide] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Trade]:
        """Get trades with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM trades WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if side:
                query += " AND side = ?"
                params.append(side)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            trades = []
            for row in cursor.fetchall():
                trades.append(Trade(**dict(row)))

            return trades

    def update_bot_state(self, **kwargs):
        """Update bot state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = []
            params = []

            for key, value in kwargs.items():
                if hasattr(BotState, key):
                    updates.append(f"{key} = ?")
                    params.append(value)

            if updates:
                updates.append("last_update = ?")
                params.append(datetime.utcnow())

                query = f"UPDATE bot_state SET {', '.join(updates)} WHERE id = 1"
                cursor.execute(query, params)

                logger.debug(f"Updated bot state: {kwargs}")

    def get_bot_state(self) -> BotState:
        """Get current bot state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM bot_state WHERE id = 1")
            row = cursor.fetchone()

            if row:
                return BotState(**dict(row))

            # Should never happen due to initialization
            return BotState()

    def save_market_snapshot(self, snapshot: MarketSnapshot):
        """Save a market snapshot."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO market_snapshots (
                    symbol, price, rsi, volatility, volume_24h,
                    price_change_24h, ma_short, ma_long, trend, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.symbol,
                    snapshot.price,
                    snapshot.rsi,
                    snapshot.volatility,
                    snapshot.volume_24h,
                    snapshot.price_change_24h,
                    snapshot.ma_short,
                    snapshot.ma_long,
                    snapshot.trend,
                    snapshot.timestamp,
                ),
            )

    def get_performance_metrics(
        self, symbol: Optional[str] = None, days: int = 30
    ) -> PerformanceMetrics:
        """Calculate performance metrics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Base query
            base_where = "WHERE status = 'FILLED'"
            params = []

            if symbol:
                base_where += " AND symbol = ?"
                params.append(symbol)

            if days > 0:
                start_date = datetime.utcnow() - timedelta(days=days)
                base_where += " AND timestamp >= ?"
                params.append(start_date)

            # Get trade statistics
            cursor.execute(
                f"""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN side = 'SELL' AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN side = 'SELL' AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(CASE WHEN side = 'SELL' THEN profit_loss ELSE 0 END) as total_profit_loss,
                    AVG(CASE WHEN side = 'SELL' AND profit_loss > 0 THEN profit_loss ELSE NULL END) as avg_profit,
                    AVG(CASE WHEN side = 'SELL' AND profit_loss < 0 THEN profit_loss ELSE NULL END) as avg_loss,
                    MAX(CASE WHEN side = 'SELL' THEN profit_loss ELSE NULL END) as best_trade,
                    MIN(CASE WHEN side = 'SELL' THEN profit_loss ELSE NULL END) as worst_trade,
                    AVG(CASE WHEN side = 'SELL' THEN holding_time_hours ELSE NULL END) as avg_holding_time
                FROM trades
                {base_where}
            """,
                params,
            )

            row = cursor.fetchone()

            metrics = PerformanceMetrics()
            if row:
                metrics.total_trades = row["total_trades"] or 0
                metrics.winning_trades = row["winning_trades"] or 0
                metrics.losing_trades = row["losing_trades"] or 0
                metrics.total_profit_loss = row["total_profit_loss"] or 0.0
                metrics.average_profit = row["avg_profit"] or 0.0
                metrics.average_loss = row["avg_loss"] or 0.0
                metrics.best_trade_profit = row["best_trade"] or 0.0
                metrics.worst_trade_loss = row["worst_trade"] or 0.0
                metrics.average_holding_time_hours = row["avg_holding_time"] or 0.0

                # Calculate derived metrics
                total_sells = metrics.winning_trades + metrics.losing_trades
                if total_sells > 0:
                    metrics.win_rate = metrics.winning_trades / total_sells

                if metrics.average_loss < 0:
                    metrics.profit_factor = abs(metrics.average_profit / metrics.average_loss)

            return metrics

    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old market snapshots to prevent database bloat."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            cursor.execute(
                """
                DELETE FROM market_snapshots
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )

            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old market snapshots")

                # Vacuum to reclaim space
                cursor.execute("VACUUM")


# Singleton instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get database singleton instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
