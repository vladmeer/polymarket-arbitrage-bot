"""
Utility Module - Helper Functions

This module provides simple helper functions for common operations.
These are convenience wrappers that make the code easier to use.

Example:
    from src.utils import create_bot_from_env, validate_address

    # Quick bot creation from environment
    bot = create_bot_from_env()

    # Validate an Ethereum address
    if validate_address("0x..."):
        print("Valid address!")
"""

from typing import Tuple

from .config import Config, get_env
from .bot import TradingBot
from .crypto import verify_private_key


def validate_address(address: str) -> bool:
    """
    Check if a string is a valid Ethereum address.

    Args:
        address: The address to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_address("0x1234567890123456789012345678901234567890")
        True
        >>> validate_address("invalid")
        False
    """
    if not address:
        return False

    # Must start with 0x and be 42 characters total
    if not address.startswith("0x"):
        return False

    if len(address) != 42:
        return False

    # Must be valid hex
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def validate_private_key(key: str) -> Tuple[bool, str]:
    """
    Validate and normalize a private key.

    Args:
        key: Private key (with or without 0x prefix)

    Returns:
        Tuple of (is_valid, normalized_key_or_error_message)

    Example:
        >>> is_valid, result = validate_private_key("abc123...")
        >>> if is_valid:
        ...     print(f"Key: {result}")
        ... else:
        ...     print(f"Error: {result}")
    """
    if not key:
        return False, "Private key cannot be empty"

    is_valid, result = verify_private_key(key)
    if is_valid:
        return True, result

    if "64 hex characters" in result:
        return False, "Private key must be 64 hex characters (32 bytes)"
    if "invalid characters" in result.lower():
        return False, "Private key contains invalid characters"

    return False, result


def format_price(price: float, decimals: int = 2) -> str:
    """
    Format a price for display.

    Args:
        price: Price value (0-1)
        decimals: Number of decimal places

    Returns:
        Formatted price string with percentage

    Example:
        >>> format_price(0.65)
        '0.65 (65%)'
    """
    percentage = price * 100
    return f"{price:.{decimals}f} ({percentage:.0f}%)"


def format_usdc(amount: float, decimals: int = 2) -> str:
    """
    Format a USDC amount for display.

    Args:
        amount: Amount in USDC
        decimals: Number of decimal places

    Returns:
        Formatted amount string

    Example:
        >>> format_usdc(10.5)
        '$10.50 USDC'
    """
    return f"${amount:.{decimals}f} USDC"


def create_bot_from_env() -> TradingBot:
    """
    Create a TradingBot instance from environment variables.

    This is the simplest way to create a bot - just set your
    environment variables and call this function.

    Required environment variables:
        POLY_PRIVATE_KEY: Your wallet private key
        POLY_PROXY_WALLET: Your Polymarket Proxy wallet address

    Optional environment variables:
        POLY_BUILDER_API_KEY: Builder API key (for gasless)
        POLY_BUILDER_API_SECRET: Builder API secret
        POLY_BUILDER_API_PASSPHRASE: Builder API passphrase

    Returns:
        Configured TradingBot instance

    Raises:
        ValueError: If required environment variables are missing

    Example:
        >>> import os
        >>> os.environ["POLY_PRIVATE_KEY"] = "0x..."
        >>> os.environ["POLY_PROXY_WALLET"] = "0x..."
        >>> bot = create_bot_from_env()
        >>> print(bot.is_initialized())
        True
    """
    private_key = get_env("PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "POLY_PRIVATE_KEY environment variable is required. "
            "Set it with: export POLY_PRIVATE_KEY=your_key"
        )

    safe_address = get_env("PROXY_WALLET")
    if not safe_address:
        raise ValueError(
            "POLY_PROXY_WALLET environment variable is required. "
            "Set it with: export POLY_PROXY_WALLET=0x..."
        )

    # Load config from environment
    config = Config.from_env()

    # Create and return bot
    return TradingBot(
        config=config,
        private_key=private_key
    )


def truncate_address(address: str, chars: int = 6) -> str:
    """
    Truncate an address for display.

    Args:
        address: Full Ethereum address
        chars: Number of characters to show at start/end

    Returns:
        Truncated address string

    Example:
        >>> truncate_address("0x1234567890123456789012345678901234567890")
        '0x1234...7890'
    """
    if not address or len(address) < chars * 2 + 2:
        return address
    return f"{address[:chars + 2]}...{address[-chars:]}"


def truncate_token_id(token_id: str, chars: int = 8) -> str:
    """
    Truncate a token ID for display.

    Args:
        token_id: Full token ID
        chars: Number of characters to show

    Returns:
        Truncated token ID string

    Example:
        >>> truncate_token_id("123456789012345678901234567890")
        '12345678...'
    """
    if not token_id or len(token_id) <= chars:
        return token_id
    return f"{token_id[:chars]}..."


# Re-export commonly used functions
__all__ = [
    "validate_address",
    "validate_private_key",
    "format_price",
    "format_usdc",
    "get_env",
    "create_bot_from_env",
    "truncate_address",
    "truncate_token_id",
]
