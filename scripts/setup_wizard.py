#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Initial Setup Wizard

Interactive setup wizard that guides users through the initial configuration
of the Polymarket trading bot. This script should be run once to securely
configure and store your credentials.

Setup Process:
1. Input private key (encrypted and stored securely on disk)
2. Set encryption password (required to decrypt key file)
3. Configure Polymarket Safe address
4. Configure Builder Program credentials (optional, for gasless trading)
5. Generate config.yaml configuration file

Security Features:
    - Private keys are encrypted using PBKDF2 key derivation (480,000 iterations)
    - Fernet symmetric encryption (AES-128-CBC with HMAC)
    - Unique salt generated for each encryption
    - Password is never stored, only used for encryption/decryption

Usage:
    python scripts/setup_wizard.py

Output:
    - Creates credentials/ directory with encrypted key file
    - Generates config.yaml in the project root
    - Sets appropriate file permissions (0600) for security

Note:
    This script should only be run once during initial setup. If you need
    to update credentials, you can run this script again or manually edit
    the config.yaml file.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from getpass import getpass
from eth_account import Account
import yaml

from src.crypto import KeyManager, verify_private_key
from src.config import Config


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def print_step(step: int, total: int, title: str) -> None:
    print(f"\n{Colors.BOLD}Step {step}/{total}: {title}{Colors.RESET}")


def input_private_key() -> str:
    """Get and validate private key from user."""
    print("Enter your MetaMask private key (will be encrypted and stored securely)")
    print(f"{Colors.YELLOW}Tip: Open MetaMask → Account Details → Export Private Key{Colors.RESET}\n")

    while True:
        private_key = getpass(f"{Colors.BOLD}Private Key{Colors.RESET}: ").strip()

        if not private_key:
            print_error("Private key cannot be empty")
            continue

        # Normalize and validate
        is_valid, result = verify_private_key(private_key)

        if is_valid:
            return result
        else:
            print_error(result)
            continue


def input_password() -> str:
    """Get and confirm encryption password."""
    print("Set a password to encrypt your private key")
    print(f"{Colors.YELLOW}This password is required to start the trading bot{Colors.RESET}\n")

    while True:
        password = getpass(f"{Colors.BOLD}Password{Colors.RESET}: ").strip()

        if len(password) < 8:
            print_error("Password must be at least 8 characters")
            continue

        confirm = getpass(f"{Colors.BOLD}Confirm Password{Colors.RESET}: ").strip()

        if password != confirm:
            print_error("Passwords do not match")
            continue

        return password


def input_safe_address() -> str:
    """Get Safe address from user."""
    print("Enter your Polymarket Safe/Proxy wallet address")
    print(f"{Colors.YELLOW}Tip: polymarket.com/settings → General → Wallet Address{Colors.RESET}\n")

    while True:
        address = input(f"{Colors.BOLD}Safe Address{Colors.RESET}: ").strip().lower()

        if not address:
            print_error("Address cannot be empty")
            continue

        if not address.startswith("0x") or len(address) != 42:
            print_error("Invalid Ethereum address format")
            continue

        return address


def input_builder_credentials() -> dict:
    """Get Builder Program credentials (optional)."""
    print(f"{Colors.BLUE}Builder Program Credentials (optional){Colors.RESET}")
    print("If you have Builder Program access, enter your credentials for gasless trading")
    print(f"{Colors.YELLOW}Leave empty to skip (you'll pay gas fees yourself){Colors.RESET}\n")

    api_key = input(f"{Colors.BOLD}Builder API Key{Colors.RESET} (Enter to skip): ").strip()
    if not api_key:
        return {}

    api_secret = getpass(f"{Colors.BOLD}Builder Secret{Colors.RESET}: ").strip()
    api_passphrase = getpass(f"{Colors.BOLD}Builder Passphrase{Colors.RESET}: ").strip()

    if not api_secret or not api_passphrase:
        print_warning("Incomplete Builder credentials, skipping gasless mode")

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "api_passphrase": api_passphrase
    }


def create_config(
    safe_address: str,
    builder_creds: dict,
    data_dir: str = "credentials"
) -> Config:
    """Create Config object."""
    config = Config(
        safe_address=safe_address,
        data_dir=data_dir,
        use_gasless=bool(builder_creds),
    )

    if builder_creds:
        from src.config import BuilderConfig
        config.builder = BuilderConfig(
            api_key=builder_creds.get("api_key", ""),
            api_secret=builder_creds.get("api_secret", ""),
            api_passphrase=builder_creds.get("api_passphrase", ""),
        )

    return config


def main():
    """Main setup function."""
    print_header("Polymarket Arbitrage Bot Setup")
    print(f"{Colors.BLUE}This script will help you configure the trading bot.{Colors.RESET}")
    print(f"{Colors.BLUE}Your private key will be encrypted and stored securely.{Colors.RESET}")

    # Step 1: Private Key
    print_step(1, 4, "Private Key")
    private_key = input_private_key()
    wallet = Account.from_key(private_key)
    print_success(f"Wallet address: {wallet.address}")

    # Step 2: Encryption Password
    print_step(2, 4, "Encryption Password")
    password = input_password()
    print_success("Password set")

    # Step 3: Safe Address
    print_step(3, 4, "Safe Address")
    safe_address = input_safe_address()
    print_success(f"Safe address: {safe_address}")

    # Step 4: Builder Credentials
    print_step(4, 4, "Builder Credentials (Optional)")
    builder_creds = input_builder_credentials()

    # Create directories
    print("\nCreating directories...")
    Path("credentials").mkdir(exist_ok=True)
    print_success("Created credentials/ directory")

    # Encrypt and save private key
    print("\nEncrypting private key...")
    manager = KeyManager()
    key_path = manager.encrypt_and_save(private_key, password, "credentials/encrypted_key.json")
    print_success(f"Encrypted key saved to {key_path}")

    # Create config.yaml
    print("\nCreating config.yaml...")
    config = create_config(safe_address, builder_creds)
    config.save("config.yaml")
    print_success("config.yaml created")

    # Summary
    print_header("Setup Complete!")
    print(f"{Colors.GREEN}✓{Colors.RESET} Private key encrypted and saved")
    print(f"{Colors.GREEN}✓{Colors.RESET} Config file created")
    print(f"{Colors.GREEN}✓{Colors.RESET} Ready to trade!\n")

    print(f"{Colors.BOLD}Next steps:{Colors.RESET}")
    print("1. Test the setup: python scripts/bot_cli.py")
    print("2. Customize config.yaml if needed")
    print("3. Build your trading strategy!\n")

    if builder_creds:
        print(f"{Colors.GREEN}Gasless mode: ENABLED{Colors.RESET}")
    else:
        print_warning("Gasless mode: DISABLED (no Builder credentials)")
        print(f"{Colors.YELLOW}To enable later, add Builder credentials to config.yaml{Colors.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)
