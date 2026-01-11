#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Real-time Orderbook Terminal UI

A beautiful terminal-based user interface for viewing real-time orderbook
data for Polymarket 15-minute prediction markets. This tool provides an
interactive display of market depth, prices, and market information.

Features:
    - Real-time WebSocket orderbook updates with live refresh
    - Dual orderbook display (Up/Down tokens side-by-side)
    - Market countdown timer showing time until market resolution
    - Price history tracking with visual indicators
    - Configurable orderbook depth levels
    - Color-coded display for easy reading
    - Automatic market discovery for selected coin

Usage:
    # View ETH 15-minute market orderbook
    python apps/orderbook_viewer.py --coin ETH

    # View BTC market with custom depth
    python apps/orderbook_viewer.py --coin BTC --levels 10

    # Full argument list
    python apps/orderbook_viewer.py --coin ETH --levels 5

Arguments:
    --coin      Coin symbol (BTC, ETH, SOL, XRP) [default: ETH]
    --levels    Number of price levels to display [default: 5]

Prerequisites:
    - Python 3.8 or higher
    - All dependencies installed (see requirements.txt)
    - Terminal that supports ANSI color codes (most modern terminals)

Note:
    This is a read-only monitoring tool. No trades are executed.
    Press Ctrl+C to exit the application.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Suppress noisy logs
logging.getLogger("src.websocket_client").setLevel(logging.WARNING)

# Auto-load .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import MarketManager, PriceTracker, Colors
from lib.terminal_utils import format_countdown


class OrderbookTUI:
    """Real-time orderbook viewer."""

    def __init__(self, coin: str = "ETH"):
        """Initialize TUI."""
        self.coin = coin.upper()
        self.market = MarketManager(coin=self.coin)
        self.prices = PriceTracker()
        self.running = False

    async def run(self) -> None:
        """Run the TUI."""
        self.running = True

        # Register callbacks
        @self.market.on_book_update
        async def handle_book(snapshot):  # pyright: ignore[reportUnusedFunction]
            for side, token_id in self.market.token_ids.items():
                if token_id == snapshot.asset_id:
                    self.prices.record(side, snapshot.mid_price)
                    break

        @self.market.on_connect
        def on_connect():  # pyright: ignore[reportUnusedFunction]
            pass

        @self.market.on_disconnect
        def on_disconnect():  # pyright: ignore[reportUnusedFunction]
            pass

        # Start market manager
        if not await self.market.start():
            print(f"{Colors.RED}Failed to start market manager{Colors.RESET}")
            return

        await self.market.wait_for_data(timeout=5.0)

        try:
            while self.running:
                self.render()
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.market.stop()

    def render(self) -> None:
        """Render the display."""
        lines = []

        # Header
        ws_status = f"{Colors.GREEN}Connected{Colors.RESET}" if self.market.is_connected else f"{Colors.RED}Disconnected{Colors.RESET}"
        market = self.market.current_market
        countdown = "--:--"
        if market:
            mins, secs = market.get_countdown()
            countdown = format_countdown(mins, secs)

        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Orderbook TUI{Colors.RESET} | {self.coin} | {ws_status} | Ends: {countdown}")
        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        # Market info
        if market:
            lines.append(f"Market: {market.question}")
            lines.append(f"Slug: {market.slug}")
            lines.append("")

        # Orderbook display
        up_ob = self.market.get_orderbook("up")
        down_ob = self.market.get_orderbook("down")

        lines.append(f"{Colors.GREEN}{'UP':^39}{Colors.RESET}|{Colors.RED}{'DOWN':^39}{Colors.RESET}")
        lines.append(f"{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}|{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}")
        lines.append("-" * 80)

        # Get 10 levels for TUI
        up_bids = up_ob.bids[:10] if up_ob else []
        up_asks = up_ob.asks[:10] if up_ob else []
        down_bids = down_ob.bids[:10] if down_ob else []
        down_asks = down_ob.asks[:10] if down_ob else []

        for i in range(10):
            up_bid = f"{up_bids[i].price:>9.4f} {up_bids[i].size:>9.1f}" if i < len(up_bids) else f"{'--':>9} {'--':>9}"
            up_ask = f"{up_asks[i].price:>9.4f} {up_asks[i].size:>9.1f}" if i < len(up_asks) else f"{'--':>9} {'--':>9}"
            down_bid = f"{down_bids[i].price:>9.4f} {down_bids[i].size:>9.1f}" if i < len(down_bids) else f"{'--':>9} {'--':>9}"
            down_ask = f"{down_asks[i].price:>9.4f} {down_asks[i].size:>9.1f}" if i < len(down_asks) else f"{'--':>9} {'--':>9}"
            lines.append(f"{up_bid} | {up_ask}|{down_bid} | {down_ask}")

        lines.append("-" * 80)

        # Summary
        up_mid = up_ob.mid_price if up_ob else 0
        down_mid = down_ob.mid_price if down_ob else 0
        up_spread = self.market.get_spread("up")
        down_spread = self.market.get_spread("down")

        lines.append(
            f"Mid: {Colors.GREEN}{up_mid:.4f}{Colors.RESET}  Spread: {up_spread:.4f}           |"
            f"Mid: {Colors.RED}{down_mid:.4f}{Colors.RESET}  Spread: {down_spread:.4f}"
        )

        # Price history stats
        up_history = self.prices.get_history_count("up")
        down_history = self.prices.get_history_count("down")

        up_vol = self.prices.get_volatility("up", 60)
        down_vol = self.prices.get_volatility("down", 60)

        lines.append("")
        lines.append(f"History: UP={up_history} DOWN={down_history} | 60s Volatility: UP={up_vol:.4f} DOWN={down_vol:.4f}")

        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        lines.append(f"{Colors.DIM}Press Ctrl+C to exit{Colors.RESET}")

        # Render
        output = "\033[H\033[J" + "\n".join(lines)
        print(output, flush=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orderbook TUI for Polymarket 15-minute markets"
    )
    parser.add_argument(
        "--coin",
        type=str,
        default="ETH",
        choices=["BTC", "ETH", "SOL", "XRP"],
        help="Coin to monitor (default: ETH)"
    )

    args = parser.parse_args()

    tui = OrderbookTUI(coin=args.coin)

    try:
        asyncio.run(tui.run())
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
