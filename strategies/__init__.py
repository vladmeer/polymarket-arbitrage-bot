"""
Polymarket Arbitrage Bot - Trading Strategy Implementations

A collection of ready-to-use trading strategies for Polymarket prediction
markets. This package provides both base classes for custom strategies and
pre-built strategy implementations.

Available Strategies:
    - base: Abstract base class for implementing custom strategies
    - flash_crash: Volatility trading strategy for 15-minute markets

Usage:
    # Use pre-built strategy
    from strategies.flash_crash_strategy import FlashCrashStrategy, FlashCrashConfig
    from src import TradingBot

    bot = TradingBot(...)
    config = FlashCrashConfig(coin="BTC", drop_threshold=0.30)
    strategy = FlashCrashStrategy(bot, config)
    await strategy.run()

    # Or create custom strategy
    from strategies.base_strategy import BaseStrategy, StrategyConfig

    class MyStrategy(BaseStrategy):
        async def on_book_update(self, snapshot):
            # Your trading logic
            pass

Note:
    All strategies are built on top of the BaseStrategy class, which
    provides common functionality like market management, price tracking,
    and position management. Custom strategies should inherit from
    BaseStrategy for maximum compatibility.
"""

from strategies.base_strategy import BaseStrategy, StrategyConfig
from strategies.flash_crash_strategy import FlashCrashStrategy, FlashCrashConfig

__all__ = [
    "BaseStrategy",
    "StrategyConfig",
    "FlashCrashStrategy",
    "FlashCrashConfig",
]
