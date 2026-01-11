"""
Polymarket Arbitrage Bot - Strategy Base Class

Abstract base class that provides the foundation for implementing custom
trading strategies. This class handles common functionality including
market management, price tracking, position management, and lifecycle
control.

Features:
    - Common lifecycle methods (start, stop, run, cleanup)
    - Integration with lib components:
      * MarketManager: Market discovery and WebSocket management
      * PriceTracker: Real-time price tracking and pattern detection
      * PositionManager: Position tracking with take-profit/stop-loss
    - Built-in logging and status display utilities
    - Event-driven architecture with async callbacks

Usage:
    from strategies.base_strategy import BaseStrategy, StrategyConfig
    from src import TradingBot

    class MyStrategy(BaseStrategy):
        async def on_book_update(self, snapshot):
            \"\"\"Handle orderbook updates.\"\"\"
            # Your trading logic here
            mid_price = snapshot.mid_price
            if mid_price < 0.3:
                await self.bot.place_order(...)

        async def on_tick(self, prices):
            \"\"\"Called each strategy tick (polling interval).\"\"\"
            # Periodic logic here
            pass

    # Initialize and run
    bot = TradingBot(...)
    config = StrategyConfig(...)
    strategy = MyStrategy(bot, config)
    await strategy.run()

Note:
    Subclasses must implement on_book_update() or on_tick() methods
    to define the strategy's trading logic. The base class handles
    all infrastructure concerns automatically.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List

from lib.terminal_utils import LogBuffer, log
from lib.market_manager import MarketManager, MarketInfo
from lib.price_tracker import PriceTracker
from lib.position_manager import PositionManager
from src.bot import TradingBot
from src.websocket_client import OrderbookSnapshot


@dataclass
class StrategyConfig:
    """Base strategy configuration."""

    coin: str = "ETH"
    size: float = 5.0  # USDC size per trade
    max_positions: int = 1
    take_profit: float = 0.10
    stop_loss: float = 0.05

    # Market settings
    market_check_interval: float = 30.0
    auto_switch_market: bool = True

    # Price tracking
    price_lookback_seconds: int = 10
    price_history_size: int = 100

    # Display settings
    update_interval: float = 0.1
    order_refresh_interval: float = 30.0  # Seconds between order refreshes


class BaseStrategy(ABC):
    """
    Base class for trading strategies.

    Provides common infrastructure:
    - MarketManager for WebSocket and market discovery
    - PriceTracker for price history
    - PositionManager for positions and TP/SL
    - Logging and status display
    """

    def __init__(self, bot: TradingBot, config: StrategyConfig):
        """
        Initialize base strategy.

        Args:
            bot: TradingBot instance for order execution
            config: Strategy configuration
        """
        self.bot = bot
        self.config = config

        # Core components
        self.market = MarketManager(
            coin=config.coin,
            market_check_interval=config.market_check_interval,
            auto_switch_market=config.auto_switch_market,
        )

        self.prices = PriceTracker(
            lookback_seconds=config.price_lookback_seconds,
            max_history=config.price_history_size,
        )

        self.positions = PositionManager(
            take_profit=config.take_profit,
            stop_loss=config.stop_loss,
            max_positions=config.max_positions,
        )

        # State
        self.running = False
        self._status_mode = False

        # Logging
        self._log_buffer = LogBuffer(max_size=5)

        # Open orders cache (refreshed in background)
        self._cached_orders: List[dict] = []
        self._last_order_refresh: float = 0
        self._order_refresh_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.market.is_connected

    @property
    def current_market(self) -> Optional[MarketInfo]:
        """Get current market info."""
        return self.market.current_market

    @property
    def token_ids(self) -> Dict[str, str]:
        """Get current token IDs."""
        return self.market.token_ids

    @property
    def open_orders(self) -> List[dict]:
        """Get cached open orders."""
        return self._cached_orders

    def _refresh_orders_sync(self) -> List[dict]:
        """Refresh open orders synchronously (called via to_thread)."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.bot.get_open_orders())
            finally:
                loop.close()
        except Exception:
            return []

    async def _do_order_refresh(self) -> None:
        """Background task to refresh orders without blocking."""
        try:
            orders = await asyncio.to_thread(self._refresh_orders_sync)
            self._cached_orders = orders
        except Exception:
            pass
        finally:
            self._order_refresh_task = None

    def _maybe_refresh_orders(self) -> None:
        """Schedule order refresh if interval has passed (fire-and-forget)."""
        now = time.time()
        if now - self._last_order_refresh > self.config.order_refresh_interval:
            # Don't start new refresh if one is already running
            if self._order_refresh_task is not None and not self._order_refresh_task.done():
                return
            self._last_order_refresh = now
            # Fire and forget - doesn't block main loop
            self._order_refresh_task = asyncio.create_task(self._do_order_refresh())

    def log(self, msg: str, level: str = "info") -> None:
        """
        Log a message.

        Args:
            msg: Message to log
            level: Log level (info, success, warning, error, trade)
        """
        if self._status_mode:
            self._log_buffer.add(msg, level)
        else:
            log(msg, level)

    async def start(self) -> bool:
        """
        Start the strategy.

        Returns:
            True if started successfully
        """
        self.running = True

        # Register callbacks on market manager
        @self.market.on_book_update
        async def handle_book(snapshot: OrderbookSnapshot):  # pyright: ignore[reportUnusedFunction]
            # Record price
            for side, token_id in self.token_ids.items():
                if token_id == snapshot.asset_id:
                    self.prices.record(side, snapshot.mid_price)
                    break

            # Delegate to subclass
            await self.on_book_update(snapshot)

        @self.market.on_market_change
        def handle_market_change(old_slug: str, new_slug: str):  # pyright: ignore[reportUnusedFunction]
            self.log(f"Market changed: {old_slug} -> {new_slug}", "warning")
            self.prices.clear()
            self.on_market_change(old_slug, new_slug)

        @self.market.on_connect
        def handle_connect():  # pyright: ignore[reportUnusedFunction]
            self.log("WebSocket connected", "success")
            self.on_connect()

        @self.market.on_disconnect
        def handle_disconnect():  # pyright: ignore[reportUnusedFunction]
            self.log("WebSocket disconnected", "warning")
            self.on_disconnect()

        # Start market manager
        if not await self.market.start():
            self.running = False
            return False

        # Wait for initial data
        if not await self.market.wait_for_data(timeout=5.0):
            self.log("Timeout waiting for market data", "warning")

        return True

    async def stop(self) -> None:
        """Stop the strategy."""
        self.running = False

        # Cancel order refresh task if running
        if self._order_refresh_task is not None:
            self._order_refresh_task.cancel()
            try:
                await self._order_refresh_task
            except asyncio.CancelledError:
                pass
            self._order_refresh_task = None

        await self.market.stop()

    async def run(self) -> None:
        """Main strategy loop."""
        try:
            if not await self.start():
                self.log("Failed to start strategy", "error")
                return

            self._status_mode = True

            while self.running:
                # Get current prices
                prices = self._get_current_prices()

                # Call tick handler
                await self.on_tick(prices)

                # Check position exits
                await self._check_exits(prices)

                # Refresh orders in background (fire-and-forget)
                self._maybe_refresh_orders()

                # Update display
                self.render_status(prices)

                await asyncio.sleep(self.config.update_interval)

        except KeyboardInterrupt:
            self.log("Strategy stopped by user")
        finally:
            await self.stop()
            self._print_summary()

    def _get_current_prices(self) -> Dict[str, float]:
        """Get current prices from market manager."""
        prices = {}
        for side in ["up", "down"]:
            price = self.market.get_mid_price(side)
            if price > 0:
                prices[side] = price
        return prices

    async def _check_exits(self, prices: Dict[str, float]) -> None:
        """Check and execute exits for all positions."""
        exits = self.positions.check_all_exits(prices)

        for position, exit_type, pnl in exits:
            if exit_type == "take_profit":
                self.log(
                    f"TAKE PROFIT: {position.side.upper()} PnL: +${pnl:.2f}",
                    "success"
                )
            elif exit_type == "stop_loss":
                self.log(
                    f"STOP LOSS: {position.side.upper()} PnL: ${pnl:.2f}",
                    "warning"
                )

            # Execute sell
            await self.execute_sell(position, prices.get(position.side, 0))

    async def execute_buy(self, side: str, current_price: float) -> bool:
        """
        Execute market buy order.

        Args:
            side: "up" or "down"
            current_price: Current market price

        Returns:
            True if order placed successfully
        """
        token_id = self.token_ids.get(side)
        if not token_id:
            self.log(f"No token ID for {side}", "error")
            return False

        size = self.config.size / current_price
        buy_price = min(current_price + 0.02, 0.99)

        self.log(f"BUY {side.upper()} @ {current_price:.4f} size={size:.2f}", "trade")

        result = await self.bot.place_order(
            token_id=token_id,
            price=buy_price,
            size=size,
            side="BUY"
        )

        if result.success:
            self.log(f"Order placed: {result.order_id}", "success")
            self.positions.open_position(
                side=side,
                token_id=token_id,
                entry_price=current_price,
                size=size,
                order_id=result.order_id,
            )
            return True
        else:
            self.log(f"Order failed: {result.message}", "error")
            return False

    async def execute_sell(self, position: Position, current_price: float) -> bool:
        """
        Execute sell order to close position.

        Args:
            position: Position to close
            current_price: Current price

        Returns:
            True if order placed
        """
        sell_price = max(current_price - 0.02, 0.01)
        pnl = position.get_pnl(current_price)

        result = await self.bot.place_order(
            token_id=position.token_id,
            price=sell_price,
            size=position.size,
            side="SELL"
        )

        if result.success:
            self.log(f"Sell order: {result.order_id} PnL: ${pnl:+.2f}", "success")
            self.positions.close_position(position.id, realized_pnl=pnl)
            return True
        else:
            self.log(f"Sell failed: {result.message}", "error")
            return False

    def _print_summary(self) -> None:
        """Print session summary."""
        self._status_mode = False
        print()
        stats = self.positions.get_stats()
        self.log("Session Summary:")
        self.log(f"  Trades: {stats['trades_closed']}")
        self.log(f"  Total PnL: ${stats['total_pnl']:+.2f}")
        self.log(f"  Win rate: {stats['win_rate']:.1f}%")

    # Abstract methods to implement in subclasses

    @abstractmethod
    async def on_book_update(self, snapshot: OrderbookSnapshot) -> None:
        """
        Handle orderbook update.

        Called when new orderbook data is received.

        Args:
            snapshot: OrderbookSnapshot from WebSocket
        """
        pass

    @abstractmethod
    async def on_tick(self, prices: Dict[str, float]) -> None:
        """
        Handle strategy tick.

        Called on each iteration of the main loop.

        Args:
            prices: Current prices {side: price}
        """
        pass

    @abstractmethod
    def render_status(self, prices: Dict[str, float]) -> None:
        """
        Render status display.

        Called on each tick to update the display.

        Args:
            prices: Current prices
        """
        pass

    # Optional hooks (override as needed)

    def on_market_change(self, old_slug: str, new_slug: str) -> None:
        """Called when market changes."""
        pass

    def on_connect(self) -> None:
        """Called when WebSocket connects."""
        pass

    def on_disconnect(self) -> None:
        """Called when WebSocket disconnects."""
        pass
