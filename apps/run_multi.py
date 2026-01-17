#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Multi-Market Runner

Runs the Flash Crash Strategy on multiple markets simultaneously
with a condensed TUI dashboard.
"""

import os
import sys
import asyncio
import argparse
import logging
import time
from pathlib import Path
from typing import List

# Suppress noisy logs
logging.getLogger("src.websocket_client").setLevel(logging.WARNING)
logging.getLogger("src.bot").setLevel(logging.WARNING)

# Auto-load .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.terminal_utils import Colors
from src.bot import TradingBot
from src.config import Config
from apps.flash_crash_strategy import FlashCrashStrategy, FlashCrashConfig

async def run_strategies(bot: TradingBot, strategies: List[FlashCrashStrategy]):
    """Run multiple strategies concurrently."""
    tasks = [asyncio.create_task(s.run()) for s in strategies]
    
    # Hide cursor
    print("\033[?25l", end="")

    try:
        while True:
            # Build TUI Buffer
            lines = []
            lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
            lines.append(f"{Colors.BOLD} Multi-Market Flash Crash Bot{Colors.RESET}")
            lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
            
            # Header
            lines.append(
                f"{'Coin':<6} | {'Price (Up/Down)':<16} | {'Spread':<8} | {'Time':<6} | {'Trades':<6} | {'PnL':<10}"
            )
            lines.append("-" * 80)
            
            total_pnl = 0.0
            
            for s in strategies:
                market = s.market.current_market
                time_str = "--:--"
                up_price = 0.0
                down_price = 0.0
                spread = 0.0
                
                if market:
                    mins, secs = market.get_countdown()
                    time_str = f"{mins:02d}:{secs:02d}"
                    up_price = s.market.get_mid_price("up")
                    down_price = s.market.get_mid_price("down")
                    
                    # Avg spread
                    spread = (s.market.get_spread("up") + s.market.get_spread("down")) / 2
                
                stats = s.positions.get_stats()
                pnl = stats['total_pnl']
                total_pnl += pnl
                pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
                
                # Prices color
                price_str = f"{up_price:.3f} / {down_price:.3f}"
                
                line = (
                    f"{Colors.CYAN}{s.config.coin:<6}{Colors.RESET} | "
                    f"{price_str:<16} | "
                    f"{spread:<8.4f} | "
                    f"{time_str:<6} | "
                    f"{stats['trades_closed']:<6} | "
                    f"{pnl_color}${pnl:<9.2f}{Colors.RESET}"
                )
                lines.append(line)
            
            lines.append("-" * 80)
            lines.append(f"Total Session PnL: {Colors.GREEN if total_pnl >= 0 else Colors.RED}${total_pnl:.2f}{Colors.RESET}")
            lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
            
            # Show recent logs from first strategy (primary log source)
            # or merge logs? Merging is better
            lines.append(f"{Colors.BOLD}Recent Activity:{Colors.RESET}")
            
            # Collect last 5 logs from all strategies
            recent_logs = []
            for s in strategies:
                 msgs = s._log_buffer.get_messages()
                 for m in msgs:
                     recent_logs.append(f"[{s.config.coin}] {m}")
            
            # Sort simplistic or just take last 5
            # Since they are strings, we can't easily sort by time without parsing
            # Just show last 5 added
            for msg in recent_logs[-5:]:
                lines.append(msg)

            # Move cursor up and print
            output = "\033[H\033[J" + "\n".join(lines)
            print(output, flush=True)
            
            await asyncio.sleep(0.5)
            
            # Check failures
            for t in tasks:
                 if t.done():
                     t.result() # Raise exception
                     
    finally:
        print("\033[?25h", end="") # Show cursor
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-Market Runner")
    parser.add_argument("--coins", type=str, default="BTC,ETH,SOL,XRP")
    parser.add_argument("--size", type=float, default=5.0)
    parser.add_argument("--drop", type=float, default=0.30)
    
    args = parser.parse_args()
    coins = [c.strip().upper() for c in args.coins.split(",")]

    private_key = os.environ.get("POLY_PRIVATE_KEY")
    # Sanitize key here too just in case
    if private_key:
        private_key = private_key.strip().replace('"', '').replace("'", "")
        
    safe_address = os.environ.get("POLY_PROXY_WALLET")

    if not private_key or not safe_address:
        print(f"{Colors.RED}Error: CREDENTIALS MISSING{Colors.RESET}")
        sys.exit(1)

    config = Config.from_env()
    bot = TradingBot(config=config, private_key=private_key)

    if not bot.is_initialized():
        print(f"{Colors.RED}Failed to init bot{Colors.RESET}")
        sys.exit(1)

    strategies = []
    for coin in coins:
        cfg = FlashCrashConfig(
            coin=coin,
            size=args.size,
            drop_threshold=args.drop,
            render_enabled=False 
        )
        strategies.append(FlashCrashStrategy(bot, cfg))

    try:
        asyncio.run(run_strategies(bot, strategies))
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
