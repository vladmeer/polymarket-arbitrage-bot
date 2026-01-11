#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Interactive Bot Runner

Interactive command-line interface for running the Polymarket trading bot
with real-time orderbook monitoring and trading capabilities.

This script provides two initialization modes:
1. Environment Variables Mode (recommended for beginners):
   - Set POLY_PRIVATE_KEY and POLY_PROXY_WALLET in .env file
   - Simplest setup, no additional configuration required

2. Encrypted Key Mode (recommended for production):
   - Run setup first: python scripts/setup_wizard.py
   - Creates encrypted key file and config.yaml for enhanced security
   - More secure as private key is encrypted on disk

Usage:
    python scripts/bot_cli.py              # Quick demo mode
    python scripts/bot_cli.py --interactive # Interactive CLI mode

Features:
    - Interactive command-line interface
    - Real-time orderbook monitoring
    - Place and cancel orders
    - View open orders and trade history
    - Get market prices and orderbook data

Prerequisites:
    - Python 3.8 or higher
    - All dependencies installed (see requirements.txt)
    - A .env file with POLY_PRIVATE_KEY and POLY_PROXY_WALLET,
      or run scripts/setup_wizard.py to create encrypted credentials
"""

import os
import sys
import asyncio
from pathlib import Path

# Auto-load .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from getpass import getpass

from src.config import Config
from src.crypto import KeyManager, InvalidPasswordError, CryptoError
from src.bot import TradingBot


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def check_env_mode() -> bool:
    """Check if environment variables are set for direct mode."""
    private_key = os.environ.get("POLY_PRIVATE_KEY")
    safe_address = os.environ.get("POLY_PROXY_WALLET")
    return bool(private_key and safe_address)


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    config = Config.from_env()
    errors = config.validate()

    if errors:
        print_error("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    return config


def load_config() -> Config:
    """Load configuration from config.yaml."""
    if not os.path.exists("config.yaml"):
        print_error("config.yaml not found!")
        print("\nPlease run the setup first:")
        print(f"  {Colors.CYAN}python scripts/setup_wizard.py{Colors.RESET}")
        sys.exit(1)

    try:
        config = Config.load("config.yaml")
        errors = config.validate()

        if errors:
            print_error("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

        return config
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        sys.exit(1)


def get_private_key_from_env() -> str:
    """Get private key from environment variable."""
    private_key = os.environ.get("POLY_PRIVATE_KEY")
    if not private_key:
        print_error("POLY_PRIVATE_KEY environment variable not set!")
        sys.exit(1)
    return private_key


def decrypt_private_key() -> str:
    """Decrypt private key from encrypted file."""
    key_path = "credentials/encrypted_key.json"

    if not os.path.exists(key_path):
        print_error("Encrypted key not found!")
        print("\nPlease run the setup first:")
        print(f"  {Colors.CYAN}python scripts/setup_wizard.py{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.BOLD}Enter decryption password:{Colors.RESET}")

    while True:
        password = getpass("Password: ")

        try:
            manager = KeyManager()
            private_key = manager.load_and_decrypt(password, key_path)
            print_success("Private key decrypted")
            return private_key

        except InvalidPasswordError:
            print_error("Invalid password, try again")
        except CryptoError as e:
            print_error(f"Failed to decrypt: {e}")
            sys.exit(1)


def print_help() -> None:
    """Print available commands."""
    print(f"{Colors.BOLD}Available Commands:{Colors.RESET}")
    print("  help          - Show this help message")
    print("  status        - Show bot status and open orders")
    print("  place <token> <price> <size> <side> - Place an order")
    print("  cancel <order_id> - Cancel an order")
    print("  cancel-all    - Cancel all orders")
    print("  trades        - Show recent trades")
    print("  price <token> - Get market price")
    print("  exit          - Exit the bot")
    print()
    print(f"{Colors.BOLD}Examples:{Colors.RESET}")
    print("  place 0x123... 0.65 10 BUY")
    print("  cancel order_123")
    print("  price 0x123...")


async def print_status(bot: TradingBot) -> None:
    """Print bot status."""
    config = bot.config

    print(f"{Colors.BOLD}Bot Status:{Colors.RESET}")
    print(f"  Safe Address: {config.safe_address}")
    print(f"  Gasless Mode: {'Enabled' if config.use_gasless else 'Disabled'}")
    print(f"  Data Dir: {config.data_dir}")

    # Get open orders
    orders = await bot.get_open_orders()
    print(f"  Open Orders: {len(orders)}")

    if orders:
        print(f"\n{Colors.BOLD}Open Orders:{Colors.RESET}")
        for order in orders[:5]:  # Show first 5
            print(f"  - {order.get('side', '?')} {order.get('size', '?')} @ "
                  f"{order.get('price', '?')} ({order.get('tokenId', '?')[:16]}...)")
        if len(orders) > 5:
            print(f"  ... and {len(orders) - 5} more")


async def interactive_session(bot: TradingBot) -> None:
    """Run interactive trading session."""
    print_header("Polymarket Arbitrage Bot")
    print_success("Bot initialized and ready!")
    print()
    print(f"Type {Colors.CYAN}help{Colors.RESET} for available commands\n")

    while True:
        try:
            cmd = input(f"{Colors.CYAN}bot>{Colors.RESET} ").strip().lower()

            if not cmd:
                continue

            if cmd == "exit":
                print("\nGoodbye!")
                break

            elif cmd == "help":
                print_help()

            elif cmd == "status":
                await print_status(bot)

            elif cmd == "cancel-all":
                result = await bot.cancel_all_orders()
                if result.success:
                    print_success(result.message)
                else:
                    print_error(result.message)

            elif cmd.startswith("cancel"):
                parts = cmd.split()
                if len(parts) >= 2:
                    order_id = parts[1]
                    result = await bot.cancel_order(order_id)
                    if result.success:
                        print_success(f"Order {order_id} cancelled")
                    else:
                        print_error(result.message)
                else:
                    print_error("Usage: cancel <order_id>")

            elif cmd.startswith("place"):
                parts = cmd.split()
                if len(parts) >= 5:
                    _, token_id, price, size, side = parts[:5]
                    try:
                        result = await bot.place_order(
                            token_id=token_id,
                            price=float(price),
                            size=float(size),
                            side=side.upper()
                        )
                        if result.success:
                            print_success(f"Order placed: {result.order_id}")
                        else:
                            print_error(f"Order failed: {result.message}")
                    except ValueError as e:
                        print_error(f"Invalid parameters: {e}")
                else:
                    print_error("Usage: place <token_id> <price> <size> <side>")

            elif cmd.startswith("price"):
                parts = cmd.split()
                if len(parts) >= 2:
                    token_id = parts[1]
                    price_data = await bot.get_market_price(token_id)
                    if price_data:
                        print(f"Price: {price_data.get('price', 'N/A')}")
                    else:
                        print_error("Failed to get price")
                else:
                    print_error("Usage: price <token_id>")

            elif cmd == "trades":
                trades = await bot.get_trades(limit=10)
                if trades:
                    print(f"{Colors.BOLD}Recent Trades:{Colors.RESET}")
                    for trade in trades[:5]:
                        print(f"  - {trade.get('side', '?')} {trade.get('size', '?')} @ "
                              f"{trade.get('price', '?')}")
                else:
                    print("No trades yet")

            else:
                print_error(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")

        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")
        except Exception as e:
            print_error(f"Error: {e}")


async def quick_demo(bot: TradingBot) -> None:
    """Run a quick demo without interactive mode."""
    print_header("Quick Demo")

    # Show status
    await print_status(bot)

    # Get market price for default token
    if bot.config.default_token_id:
        print(f"\n{Colors.BOLD}Market Price:{Colors.RESET}")
        price_data = await bot.get_market_price(bot.config.default_token_id)
        if price_data:
            print(f"  {price_data}")
        else:
            print("  Failed to get price")
    else:
        print(f"\n{Colors.YELLOW}No default token configured.{Colors.RESET}")
        print("  Set 'default_token_id' in config.yaml to enable price lookup.")


def main():
    """Main entry point."""
    print_header("Polymarket Arbitrage Bot")

    # Check for environment variable mode
    use_env_mode = check_env_mode()

    if use_env_mode:
        # Environment variable mode
        print_success("Using environment variables mode")
        config = load_config_from_env()
        private_key = get_private_key_from_env()
        print_success(f"Configuration loaded (gasless: {config.use_gasless})")
    else:
        # Encrypted key mode (legacy)
        print(f"{Colors.YELLOW}Environment variables not found, using encrypted key mode{Colors.RESET}")
        print(f"  Tip: Set POLY_PRIVATE_KEY and POLY_PROXY_WALLET in .env for easier setup\n")

        # Load configuration
        config = load_config()
        print_success(f"Configuration loaded (gasless: {config.use_gasless})")

        # Decrypt private key
        private_key = decrypt_private_key()

    # Initialize bot
    try:
        bot = TradingBot(
            config=config,
            private_key=private_key,
        )
    except Exception as e:
        print_error(f"Failed to initialize bot: {e}")
        sys.exit(1)

    print_success("Bot initialized!")

    # Run demo or interactive session
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_session(bot))
    else:
        asyncio.run(quick_demo(bot))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)
