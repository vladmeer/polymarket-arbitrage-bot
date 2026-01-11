"""
Polymarket Arbitrage Bot - EIP-712 Order Signing

Provides EIP-712 signature functionality for Polymarket orders and
authentication messages. This module handles all cryptographic signing
operations required for order submission.

About EIP-712:
    EIP-712 is an Ethereum standard for structured data hashing and signing
    that provides better security and user experience than plain message
    signing. It allows users to sign typed data structures, making it easier
    to understand what they're signing and reducing the risk of signature
    replay attacks.

Features:
    - EIP-712 compliant order signing
    - Typed data structure definitions
    - Signature verification utilities
    - Support for all Polymarket order types

Example:
    from src.signer import OrderSigner, Order

    # Initialize signer with private key
    signer = OrderSigner(private_key="0x...")

    # Sign an order
    order = Order(
        token_id="123...",
        price=0.65,
        size=10.0,
        side="BUY",
        maker="0xYourAddress",
        expiration=time.time() + 3600
    )
    signature = signer.sign_order(order)

    # The signature can now be submitted to the Polymarket API

Security Note:
    Private keys are used only for signing operations and should never be
    logged or exposed. Always use secure key management practices.
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import to_checksum_address


# USDC has 6 decimal places
USDC_DECIMALS = 6


@dataclass
class Order:
    """
    Represents a Polymarket order.

    Attributes:
        token_id: The ERC-1155 token ID for the market outcome
        price: Price per share (0-1, e.g., 0.65 = 65%)
        size: Number of shares
        side: Order side ('BUY' or 'SELL')
        maker: The maker's wallet address (Safe/Proxy)
        nonce: Unique order nonce (usually timestamp)
        fee_rate_bps: Fee rate in basis points (usually 0)
        signature_type: Signature type (2 = Gnosis Safe)
    """
    token_id: str
    price: float
    size: float
    side: str
    maker: str
    nonce: Optional[int] = None
    fee_rate_bps: int = 0
    signature_type: int = 2

    def __post_init__(self):
        """Validate and normalize order parameters."""
        self.side = self.side.upper()
        if self.side not in ("BUY", "SELL"):
            raise ValueError(f"Invalid side: {self.side}")

        if not 0 < self.price <= 1:
            raise ValueError(f"Invalid price: {self.price}")

        if self.size <= 0:
            raise ValueError(f"Invalid size: {self.size}")

        if self.nonce is None:
            self.nonce = int(time.time())

        # Convert to integers for blockchain
        self.maker_amount = str(int(self.size * self.price * 10**USDC_DECIMALS))
        self.taker_amount = str(int(self.size * 10**USDC_DECIMALS))
        self.side_value = 0 if self.side == "BUY" else 1


class SignerError(Exception):
    """Base exception for signer operations."""
    pass


class OrderSigner:
    """
    Signs Polymarket orders using EIP-712.

    This signer handles:
    - Authentication messages (L1)
    - Order messages (for CLOB submission)

    Attributes:
        wallet: The Ethereum wallet instance
        address: The signer's address
        domain: EIP-712 domain separator
    """

    # Polymarket CLOB EIP-712 domain
    DOMAIN = {
        "name": "ClobAuthDomain",
        "version": "1",
        "chainId": 137,  # Polygon mainnet
    }

    # Order type definition for EIP-712
    ORDER_TYPES = {
        "Order": [
            {"name": "salt", "type": "uint256"},
            {"name": "maker", "type": "address"},
            {"name": "signer", "type": "address"},
            {"name": "taker", "type": "address"},
            {"name": "tokenId", "type": "uint256"},
            {"name": "makerAmount", "type": "uint256"},
            {"name": "takerAmount", "type": "uint256"},
            {"name": "expiration", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "feeRateBps", "type": "uint256"},
            {"name": "side", "type": "uint8"},
            {"name": "signatureType", "type": "uint8"},
        ]
    }

    def __init__(self, private_key: str):
        """
        Initialize signer with a private key.

        Args:
            private_key: Private key (with or without 0x prefix)

        Raises:
            ValueError: If private key is invalid
        """
        if private_key.startswith("0x"):
            private_key = private_key[2:]

        try:
            self.wallet = Account.from_key(f"0x{private_key}")
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}")

        self.address = self.wallet.address

    @classmethod
    def from_encrypted(
        cls,
        encrypted_data: dict,
        password: str
    ) -> "OrderSigner":
        """
        Create signer from encrypted private key.

        Args:
            encrypted_data: Encrypted key data
            password: Decryption password

        Returns:
            Configured OrderSigner instance

        Raises:
            InvalidPasswordError: If password is incorrect
        """
        from .crypto import KeyManager, InvalidPasswordError

        manager = KeyManager()
        private_key = manager.decrypt(encrypted_data, password)
        return cls(private_key)

    def sign_auth_message(
        self,
        timestamp: Optional[str] = None,
        nonce: int = 0
    ) -> str:
        """
        Sign an authentication message for L1 authentication.

        This signature is used to create or derive API credentials.

        Args:
            timestamp: Message timestamp (defaults to current time)
            nonce: Message nonce (usually 0)

        Returns:
            Hex-encoded signature
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        # Auth message types
        auth_types = {
            "ClobAuth": [
                {"name": "address", "type": "address"},
                {"name": "timestamp", "type": "string"},
                {"name": "nonce", "type": "uint256"},
                {"name": "message", "type": "string"},
            ]
        }

        message_data = {
            "address": self.address,
            "timestamp": timestamp,
            "nonce": nonce,
            "message": "This message attests that I control the given wallet",
        }

        signable = encode_typed_data(
            domain_data=self.DOMAIN,
            message_types=auth_types,
            message_data=message_data
        )

        signed = self.wallet.sign_message(signable)
        return "0x" + signed.signature.hex()

    def sign_order(self, order: Order) -> Dict[str, Any]:
        """
        Sign a Polymarket order.

        Args:
            order: Order instance to sign

        Returns:
            Dictionary containing order and signature

        Raises:
            SignerError: If signing fails
        """
        try:
            # Build order message for EIP-712
            order_message = {
                "salt": 0,
                "maker": to_checksum_address(order.maker),
                "signer": self.address,
                "taker": "0x0000000000000000000000000000000000000000",
                "tokenId": int(order.token_id),
                "makerAmount": int(order.maker_amount),
                "takerAmount": int(order.taker_amount),
                "expiration": 0,
                "nonce": order.nonce,
                "feeRateBps": order.fee_rate_bps,
                "side": order.side_value,
                "signatureType": order.signature_type,
            }

            # Sign the order using new API format
            signable = encode_typed_data(
                domain_data=self.DOMAIN,
                message_types=self.ORDER_TYPES,
                message_data=order_message
            )

            signed = self.wallet.sign_message(signable)

            return {
                "order": {
                    "tokenId": order.token_id,
                    "price": order.price,
                    "size": order.size,
                    "side": order.side,
                    "maker": order.maker,
                    "nonce": order.nonce,
                    "feeRateBps": order.fee_rate_bps,
                    "signatureType": order.signature_type,
                },
                "signature": "0x" + signed.signature.hex(),
                "signer": self.address,
            }

        except Exception as e:
            raise SignerError(f"Failed to sign order: {e}")

    def sign_order_dict(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        maker: str,
        nonce: Optional[int] = None,
        fee_rate_bps: int = 0
    ) -> Dict[str, Any]:
        """
        Sign an order from dictionary parameters.

        Args:
            token_id: Market token ID
            price: Price per share
            size: Number of shares
            side: 'BUY' or 'SELL'
            maker: Maker's wallet address
            nonce: Order nonce (defaults to timestamp)
            fee_rate_bps: Fee rate in basis points

        Returns:
            Dictionary containing order and signature
        """
        order = Order(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
            maker=maker,
            nonce=nonce,
            fee_rate_bps=fee_rate_bps,
        )
        return self.sign_order(order)

    def sign_message(self, message: str) -> str:
        """
        Sign a plain text message (for API key derivation).

        Args:
            message: Plain text message to sign

        Returns:
            Hex-encoded signature
        """
        from eth_account.messages import encode_defunct

        signable = encode_defunct(text=message)
        signed = self.wallet.sign_message(signable)
        return "0x" + signed.signature.hex()


# Alias for backwards compatibility
WalletSigner = OrderSigner
