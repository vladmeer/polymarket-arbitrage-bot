"""
Polymarket Arbitrage Bot - Flash Crash Trading Strategy

A volatility trading strategy designed for Polymarket's 15-minute Up/Down
markets. This strategy identifies sudden probability drops (flash crashes)
and executes trades to capitalize on market inefficiencies.

Strategy Overview:
    The Flash Crash strategy monitors 15-minute prediction markets in
    real-time and detects when either the "Up" or "Down" probability
    experiences a significant drop within a short time window. When such
    an event is detected, the strategy automatically purchases the crashed
    side, expecting a mean reversion.

Strategy Logic:
1. Auto-discover current 15-minute market for selected coin (BTC, ETH, SOL, XRP)
2. Monitor orderbook prices in real-time via WebSocket
3. Track price history and detect probability drops
4. When drop threshold is exceeded within lookback window:
   - Execute market buy order on the crashed side
5. Manage position with exit conditions:
   - Take profit: Configurable dollar amount (default: +$0.10)
   - Stop loss: Configurable dollar amount (default: -$0.05)

Usage:
    from strategies.flash_crash_strategy import FlashCrashStrategy, FlashCrashConfig
    from src import TradingBot

    bot = TradingBot(...)
    config = FlashCrashConfig(
        coin="BTC",
        drop_threshold=0.30,  # 30% probability drop
        trade_size=10.0,      # $10 trade size
        lookback_seconds=10,  # 10-second detection window
        take_profit=0.10,     # $0.10 take profit
        stop_loss=0.05        # $0.05 stop loss
    )
    strategy = FlashCrashStrategy(bot, config)
    await strategy.run()

Risk Warning:
    This strategy involves significant risk. Flash crashes can continue
    beyond expected reversion points. Always use appropriate position sizing
    and risk management. Test thoroughly before using with real funds.
"""

from dataclasses import dataclass
from typing import Dict

from lib.terminal_utils import Colors, format_countdown
from strategies.base_strategy import BaseStrategy, StrategyConfig
from src.bot import TradingBot
from src.websocket_client import OrderbookSnapshot


@dataclass
class FlashCrashConfig(StrategyConfig):
    """Flash crash strategy configuration."""

    drop_threshold: float = 0.30  # Absolute probability drop


class FlashCrashStrategy(BaseStrategy):
    """
    Flash Crash Trading Strategy.

    Monitors 15-minute markets for sudden price drops and trades
    the volatility with defined take-profit and stop-loss levels.
    """

    def __init__(self, bot: TradingBot, config: FlashCrashConfig):
        """Initialize flash crash strategy."""
        super().__init__(bot, config)
        self.flash_config = config

        # Update price tracker with our threshold
        self.prices.drop_threshold = config.drop_threshold

    async def on_book_update(self, snapshot: OrderbookSnapshot) -> None:
        """Handle orderbook update - check for flash crashes."""
        pass  # Price recording is done in base class

    async def on_tick(self, prices: Dict[str, float]) -> None:
        """Check for flash crash on each tick."""
        if not self.positions.can_open_position:
            return

        # Detect flash crash
        event = self.prices.detect_flash_crash()
        if event:
            self.log(
                f"FLASH CRASH: {event.side.upper()} "
                f"drop {event.drop:.2f} ({event.old_price:.2f} -> {event.new_price:.2f})",
                "trade"
            )
            current_price = prices.get(event.side, 0)
            if current_price > 0:
                await self.execute_buy(event.side, current_price)

    def render_status(self, prices: Dict[str, float]) -> None:
        """Render TUI status display."""
        lines = []

        # Header
        ws_status = f"{Colors.GREEN}WS{Colors.RESET}" if self.is_connected else f"{Colors.RED}REST{Colors.RESET}"
        countdown = self._get_countdown_str()
        stats = self.positions.get_stats()

        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        lines.append(
            f"{Colors.CYAN}[{self.config.coin}]{Colors.RESET} [{ws_status}] "
            f"Ends: {countdown} | Trades: {stats['trades_closed']} | PnL: ${stats['total_pnl']:+.2f}"
        )
        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        # Orderbook display
        up_ob = self.market.get_orderbook("up")
        down_ob = self.market.get_orderbook("down")

        lines.append(f"{Colors.GREEN}{'UP':^39}{Colors.RESET}|{Colors.RED}{'DOWN':^39}{Colors.RESET}")
        lines.append(f"{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}|{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}")
        lines.append("-" * 80)

        # Get 5 levels
        up_bids = up_ob.bids[:5] if up_ob else []
        up_asks = up_ob.asks[:5] if up_ob else []
        down_bids = down_ob.bids[:5] if down_ob else []
        down_asks = down_ob.asks[:5] if down_ob else []

        for i in range(5):
            up_bid = f"{up_bids[i].price:>9.4f} {up_bids[i].size:>9.1f}" if i < len(up_bids) else f"{'--':>9} {'--':>9}"
            up_ask = f"{up_asks[i].price:>9.4f} {up_asks[i].size:>9.1f}" if i < len(up_asks) else f"{'--':>9} {'--':>9}"
            down_bid = f"{down_bids[i].price:>9.4f} {down_bids[i].size:>9.1f}" if i < len(down_bids) else f"{'--':>9} {'--':>9}"
            down_ask = f"{down_asks[i].price:>9.4f} {down_asks[i].size:>9.1f}" if i < len(down_asks) else f"{'--':>9} {'--':>9}"
            lines.append(f"{up_bid} | {up_ask}|{down_bid} | {down_ask}")

        lines.append("-" * 80)

        # Summary
        up_mid = up_ob.mid_price if up_ob else prices.get("up", 0)
        down_mid = down_ob.mid_price if down_ob else prices.get("down", 0)
        up_spread = self.market.get_spread("up")
        down_spread = self.market.get_spread("down")

        lines.append(
            f"Mid: {Colors.GREEN}{up_mid:.4f}{Colors.RESET}  Spread: {up_spread:.4f}           |"
            f"Mid: {Colors.RED}{down_mid:.4f}{Colors.RESET}  Spread: {down_spread:.4f}"
        )

        # History info
        up_history = self.prices.get_history_count("up")
        down_history = self.prices.get_history_count("down")
        lines.append(
            f"History: UP={up_history}/100 DOWN={down_history}/100 | "
            f"Drop threshold: {self.flash_config.drop_threshold:.2f} in {self.config.price_lookback_seconds}s"
        )

        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        # Open Orders section
        lines.append(f"{Colors.BOLD}Open Orders:{Colors.RESET}")
        if self.open_orders:
            for order in self.open_orders[:5]:  # Show max 5 orders
                side = order.get("side", "?")
                price = float(order.get("price", 0))
                size = float(order.get("original_size", order.get("size", 0)))
                filled = float(order.get("size_matched", 0))
                order_id = order.get("id", "")[:8]
                token = order.get("asset_id", "")
                # Determine if UP or DOWN
                token_side = "UP" if token == self.token_ids.get("up") else "DOWN" if token == self.token_ids.get("down") else "?"
                color = Colors.GREEN if side == "BUY" else Colors.RED
                lines.append(f"  {color}{side:4}{Colors.RESET} {token_side:4} @ {price:.4f} Size: {size:.1f} Filled: {filled:.1f} ID: {order_id}...")
        else:
            lines.append(f"  {Colors.CYAN}(no open orders){Colors.RESET}")

        # Positions
        lines.append(f"{Colors.BOLD}Positions:{Colors.RESET}")
        all_positions = self.positions.get_all_positions()
        if all_positions:
            for pos in all_positions:
                current = prices.get(pos.side, 0)
                pnl = pos.get_pnl(current)
                pnl_pct = pos.get_pnl_percent(current)
                hold_time = pos.get_hold_time()
                color = Colors.GREEN if pnl >= 0 else Colors.RED

                lines.append(
                    f"  {Colors.BOLD}{pos.side.upper():4}{Colors.RESET} "
                    f"Entry: {pos.entry_price:.4f} | Current: {current:.4f} | "
                    f"Size: ${pos.size:.2f} | PnL: {color}${pnl:+.2f} ({pnl_pct:+.1f}%){Colors.RESET} | "
                    f"Hold: {hold_time:.0f}s"
                )
                lines.append(
                    f"       TP: {pos.take_profit_price:.4f} (+${self.config.take_profit:.2f}) | "
                    f"SL: {pos.stop_loss_price:.4f} (-${self.config.stop_loss:.2f})"
                )
        else:
            lines.append(f"  {Colors.CYAN}(no open positions){Colors.RESET}")

        # Recent logs
        if self._log_buffer.messages:
            lines.append("-" * 80)
            lines.append(f"{Colors.BOLD}Recent Events:{Colors.RESET}")
            for msg in self._log_buffer.get_messages():
                lines.append(f"  {msg}")

        # Render
        output = "\033[H\033[J" + "\n".join(lines)
        print(output, flush=True)

    def _get_countdown_str(self) -> str:
        """Get formatted countdown string."""
        market = self.current_market
        if not market:
            return "--:--"

        mins, secs = market.get_countdown()
        return format_countdown(mins, secs)

    def on_market_change(self, old_slug: str, new_slug: str) -> None:
        """Handle market change - clear price history."""
        self.prices.clear()
