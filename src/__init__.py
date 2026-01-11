"""
Polymarket Arbitrage Bot - Core Trading Library

A production-ready Python trading library for Polymarket with comprehensive
features for automated trading, order management, and real-time market data.

Key Features:
    - Encrypted private key storage (PBKDF2 + Fernet)
    - Gasless transactions via Builder Program
    - Real-time WebSocket orderbook updates
    - Modular architecture for easy extension
    - Comprehensive error handling and logging

Quick Start:
    # Option 1: From environment variables
    from src import create_bot_from_env
    bot = create_bot_from_env()

    # Option 2: Manual configuration
    from src import TradingBot, Config
    config = Config(safe_address="0x...")
    bot = TradingBot(config=config, private_key="0x...")

    # Place an order
    result = await bot.place_order(token_id, price=0.5, size=1.0, side="BUY")

Core Modules:
    bot.py            - TradingBot class (main trading interface)
    config.py         - Configuration management and loading
    client.py         - API clients (CLOB, Relayer)
    signer.py         - EIP-712 order signing and verification
    crypto.py         - Private key encryption and management
    websocket_client.py - Real-time WebSocket client for market data
    gamma_client.py   - 15-minute market discovery and information
    utils.py          - Helper functions and utilities
"""

# Core classes
from .bot import TradingBot, OrderResult
from .signer import OrderSigner, Order
from .client import ApiClient, ClobClient, RelayerClient
from .crypto import KeyManager
from .config import Config, BuilderConfig
from .gamma_client import GammaClient
from .websocket_client import MarketWebSocket, OrderbookManager, OrderbookSnapshot

# Utility functions
from .utils import (
    create_bot_from_env,
    validate_address,
    validate_private_key,
    format_price,
    format_usdc,
    truncate_address,
)

__version__ = "1.0.0"
__author__ = "Polymarket Arbitrage Bot Contributors"

__all__ = [
    # Core classes
    "TradingBot",
    "OrderResult",
    "OrderSigner",
    "Order",
    "ApiClient",
    "ClobClient",
    "RelayerClient",
    "KeyManager",
    "Config",
    "BuilderConfig",
    "GammaClient",
    "MarketWebSocket",
    "OrderbookManager",
    "OrderbookSnapshot",
    # Utility functions
    "create_bot_from_env",
    "validate_address",
    "validate_private_key",
    "format_price",
    "format_usdc",
    "truncate_address",
]
