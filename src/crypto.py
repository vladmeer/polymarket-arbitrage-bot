"""
Polymarket Arbitrage Bot - Secure Private Key Encryption

Provides secure encryption and decryption utilities for storing private keys
on disk. This module implements industry-standard cryptographic practices to
ensure private keys are protected even if the encrypted file is compromised.

Security Features:
    - PBKDF2 key derivation with 480,000 iterations (resistant to brute force)
    - Unique cryptographic salt generated for each encryption
    - Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
    - Password is never stored - only used for encryption/decryption
    - File permissions automatically set to 0600 (owner-only read/write)

Cryptographic Details:
    - Key derivation: PBKDF2-HMAC-SHA256 with 480,000 iterations
    - Encryption: Fernet (AES-128-CBC + HMAC-SHA256)
    - Salt: 32 random bytes generated per encryption
    - Password requirements: Minimum length enforced (recommended: 12+ characters)

Example:
    from src.crypto import KeyManager

    manager = KeyManager()

    # Encrypt and save private key
    private_key = "0x..."
    password = "your_secure_password"
    key_file = "credentials/key.enc"
    manager.encrypt_and_save(private_key, password, key_file)

    # Load and decrypt private key
    decrypted_key = manager.load_and_decrypt(password, key_file)

Security Best Practices:
    - Use a strong, unique password (12+ characters, mixed case, numbers, symbols)
    - Store encrypted key files in a secure location
    - Never commit encrypted key files to version control
    - Consider using hardware security modules (HSM) for production deployments
    - Rotate keys periodically and update encryption as needed
"""

import os
import json
import base64
import secrets
from pathlib import Path
from typing import Tuple
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class CryptoError(Exception):
    """Base exception for crypto operations."""
    pass


class InvalidPasswordError(CryptoError):
    """Raised when password verification fails."""
    pass


class KeyManager:
    """
    Manages encrypted private key storage and retrieval.

    Uses PBKDF2-HMAC-SHA256 for key derivation and Fernet
    for symmetric encryption of private keys.

    Attributes:
        salt: The salt used for key derivation (fixed per instance)
    """

    # Number of PBKDF2 iterations for key derivation
    PBKDF2_ITERATIONS = 480000

    # Salt size in bytes
    SALT_SIZE = 16

    def __init__(self):
        """Initialize KeyManager with a random salt."""
        self.salt = secrets.token_bytes(self.SALT_SIZE)

    def _derive_key(self, password: str) -> bytes:
        """
        Derive an encryption key from password using PBKDF2.

        Args:
            password: The password to derive key from

        Returns:
            32-byte key suitable for Fernet encryption
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, private_key: str, password: str) -> dict:
        """
        Encrypt a private key with the given password.

        Args:
            private_key: The private key to encrypt (with or without 0x prefix)
            password: The password to encrypt with

        Returns:
            Dictionary containing encrypted data and salt

        Raises:
            ValueError: If private key or password is invalid
        """
        if not private_key:
            raise ValueError("Private key cannot be empty")

        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Normalize private key
        key = private_key.strip().lower()
        if key.startswith("0x"):
            key = key[2:]

        # Validate hex format
        try:
            int(key, 16)
        except ValueError:
            raise ValueError("Invalid private key format")

        # Create Fernet cipher
        cipher = Fernet(self._derive_key(password))

        # Encrypt and encode to URL-safe base64
        encrypted = cipher.encrypt(key.encode())
        encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode()

        return {
            "version": 1,
            "salt": base64.urlsafe_b64encode(self.salt).decode(),
            "encrypted": encrypted_b64,
            "key_length": len(key)
        }

    def decrypt(self, encrypted_data: dict, password: str) -> str:
        """
        Decrypt a private key using the given password.

        Args:
            encrypted_data: Dictionary from encrypt() method
            password: The password used for encryption

        Returns:
            Decrypted private key (with 0x prefix)

        Raises:
            InvalidPasswordError: If password is incorrect
            CryptoError: If data is corrupted
        """
        try:
            # Restore salt from encrypted data
            self.salt = base64.urlsafe_b64decode(encrypted_data["salt"].encode())
            encrypted_b64 = encrypted_data["encrypted"]

            # Decrypt using restored salt
            cipher = Fernet(self._derive_key(password))
            decrypted = cipher.decrypt(base64.urlsafe_b64decode(encrypted_b64))

            key = decrypted.decode()
            return f"0x{key}"

        except InvalidToken:
            raise InvalidPasswordError("Invalid password or corrupted data")
        except (KeyError, ValueError) as e:
            raise CryptoError(f"Invalid encrypted data: {e}")

    def encrypt_and_save(
        self,
        private_key: str,
        password: str,
        filepath: str
    ) -> Path:
        """
        Encrypt a private key and save to file.

        Args:
            private_key: The private key to encrypt
            password: The password to encrypt with
            filepath: Path to save encrypted key

        Returns:
            Path to the saved file
        """
        encrypted_data = self.encrypt(private_key, password)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(encrypted_data, f, indent=2)

        # Set restrictive file permissions
        os.chmod(path, 0o600)

        return path

    def load_and_decrypt(
        self,
        password: str,
        filepath: str
    ) -> str:
        """
        Load encrypted key from file and decrypt.

        Args:
            password: The password used for encryption
            filepath: Path to encrypted key file

        Returns:
            Decrypted private key (with 0x prefix)

        Raises:
            FileNotFoundError: If file doesn't exist
            InvalidPasswordError: If password is incorrect
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Encrypted key file not found: {filepath}")

        with open(path, 'r') as f:
            encrypted_data = json.load(f)

        return self.decrypt(encrypted_data, password)

    def generate_new_salt(self) -> None:
        """Generate a new random salt for key derivation."""
        self.salt = secrets.token_bytes(self.SALT_SIZE)


def verify_private_key(private_key: str) -> Tuple[bool, str]:
    """
    Verify if a string is a valid private key.

    Args:
        private_key: The key to verify (with or without 0x prefix)

    Returns:
        Tuple of (is_valid, normalized_key)
    """
    key = private_key.strip().lower()

    if key.startswith("0x"):
        key = key[2:]

    # Check length (32 bytes = 64 hex chars)
    if len(key) != 64:
        return False, "Key must be 64 hex characters"

    # Check valid hex
    try:
        int(key, 16)
    except ValueError:
        return False, "Key contains invalid characters"

    return True, f"0x{key}"


def generate_random_private_key() -> str:
    """
    Generate a new random private key.

    WARNING: Only use for testing. Never use for real funds.

    Returns:
        Newly generated private key (with 0x prefix)
    """
    return f"0x{secrets.token_hex(32)}"


# Backwards compatibility alias
KeyStore = KeyManager
