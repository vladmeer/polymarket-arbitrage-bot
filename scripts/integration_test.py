#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Full Integration Test Suite

Comprehensive integration testing script that validates all core components
and workflows of the Polymarket trading bot. This script performs end-to-end
testing of cryptographic operations, order signing, configuration management,
API client interactions, and the complete trading bot workflow.

The test suite provides detailed, color-coded output for easy diagnosis of
any issues and ensures your bot is properly configured and ready for trading.

Usage:
    python scripts/integration_test.py

    The script automatically loads environment variables from a .env file
    in the project root directory using python-dotenv.

Prerequisites:
    - Python 3.8 or higher
    - All dependencies installed (see requirements.txt)
    - A .env file in the project root with the following variables:
        * POLY_PRIVATE_KEY (required) - Your wallet private key
        * POLY_PROXY_WALLET (required) - Your Polymarket Proxy wallet address
        * POLY_BUILDER_API_KEY (optional) - Builder Program API key for gasless trading
        * POLY_BUILDER_API_SECRET (optional) - Builder Program API secret
        * POLY_BUILDER_API_PASSPHRASE (optional) - Builder Program passphrase

Example:
    # Create .env file
    echo "POLY_PRIVATE_KEY=0x..." > .env
    echo "POLY_PROXY_WALLET=0x..." >> .env
    
    # Run tests
    python scripts/integration_test.py

Note:
    This script performs actual API calls and may incur network requests.
    Ensure you have a stable internet connection before running.
"""

import os
import sys
import tempfile
from pathlib import Path

# Auto-load .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def print_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")


def print_info(msg: str) -> None:
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")


def get_test_credentials():
    """Get test credentials from environment."""
    private_key = os.environ.get("POLY_PRIVATE_KEY", "")
    safe_address = os.environ.get("POLY_PROXY_WALLET", "")

    # Builder credentials (optional)
    builder_key = os.environ.get("POLY_BUILDER_API_KEY", "")
    builder_secret = os.environ.get("POLY_BUILDER_API_SECRET", "")
    builder_passphrase = os.environ.get("POLY_BUILDER_API_PASSPHRASE", "")

    return {
        "private_key": private_key,
        "safe_address": safe_address,
        "builder_key": builder_key,
        "builder_secret": builder_secret,
        "builder_passphrase": builder_passphrase,
    }


def test_crypto_module(private_key: str) -> bool:
    """Test the crypto module."""
    print_header("1. Testing Crypto Module (crypto.py)")

    try:
        from src.crypto import KeyManager, verify_private_key

        # Verify private key format
        is_valid, result = verify_private_key(private_key)
        if not is_valid:
            print_error(f"Private key validation failed: {result}")
            return False
        print_success(f"Private key format valid")

        # Test encryption
        manager = KeyManager()
        password = "test_password_123"

        encrypted = manager.encrypt(private_key, password)
        print_success(f"Encryption successful: {list(encrypted.keys())}")

        # Test decryption
        decrypted = manager.decrypt(encrypted, password)

        # Normalize for comparison
        normalized_input = private_key.lower()
        if not normalized_input.startswith("0x"):
            normalized_input = "0x" + normalized_input

        if decrypted.lower() == normalized_input:
            print_success("Decryption matches original key")
        else:
            print_error("Decryption mismatch!")
            return False

        # Test file save/load
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.json")
            manager.encrypt_and_save(private_key, password, key_file)
            print_success(f"Saved encrypted key to file")

            manager2 = KeyManager()
            loaded = manager2.load_and_decrypt(password, key_file)
            if loaded.lower() == normalized_input:
                print_success("File load/decrypt successful")
            else:
                print_error("File load/decrypt mismatch!")
                return False

        return True

    except Exception as e:
        print_error(f"Crypto test failed: {e}")
        return False


def test_signer_module(private_key: str, expected_address: str) -> bool:
    """Test the signer module."""
    print_header("2. Testing Signer Module (signer.py)")

    try:
        from src.signer import OrderSigner, Order

        # Create signer
        signer = OrderSigner(private_key)
        print_success(f"Signer created: {signer.address}")

        # Verify address matches
        if signer.address.lower() == expected_address.lower():
            print_success("Signer address matches expected")
        else:
            print_warning(f"Address mismatch: expected {expected_address}")

        # Test auth signature
        auth_sig = signer.sign_auth_message()
        if auth_sig.startswith("0x") and len(auth_sig) == 132:
            print_success(f"Auth signature valid: {auth_sig[:20]}...{auth_sig[-10:]}")
        else:
            print_error(f"Invalid auth signature format")
            return False

        # Test order signing
        order = Order(
            token_id="12345678901234567890",
            price=0.65,
            size=10.0,
            side="BUY",
            maker=expected_address
        )

        signed = signer.sign_order(order)
        if "order" in signed and "signature" in signed and "signer" in signed:
            print_success(f"Order signed successfully")
            print_success(f"Signature: {signed['signature'][:20]}...{signed['signature'][-10:]}")
        else:
            print_error("Order signing failed")
            return False

        return True

    except Exception as e:
        print_error(f"Signer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_module(creds: dict) -> bool:
    """Test the config module."""
    print_header("3. Testing Config Module (config.py)")

    try:
        from src.config import Config, BuilderConfig

        # Test from_env
        config = Config.from_env()
        print_success(f"Config.from_env() successful")
        print_info(f"Safe address: {config.safe_address or '(not set)'}")
        print_info(f"Builder configured: {config.builder.is_configured()}")
        print_info(f"Gasless mode: {config.use_gasless}")

        # Test manual config
        manual_config = Config(
            safe_address=creds["safe_address"],
            builder=BuilderConfig(
                api_key=creds["builder_key"],
                api_secret=creds["builder_secret"],
                api_passphrase=creds["builder_passphrase"],
            ) if creds["builder_key"] else BuilderConfig()
        )

        errors = manual_config.validate()
        if errors:
            print_warning(f"Validation warnings: {errors}")
        else:
            print_success("Config validation passed")

        # Test save/load
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.yaml")
            manual_config.save(config_file)
            print_success("Config saved to YAML")

            loaded = Config.load(config_file)
            if loaded.safe_address == manual_config.safe_address:
                print_success("Config loaded from YAML")
            else:
                print_error("Config load mismatch")
                return False

        return True

    except Exception as e:
        print_error(f"Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bot_module(creds: dict) -> bool:
    """Test the bot module."""
    print_header("4. Testing Bot Module (bot.py)")

    try:
        from src.bot import TradingBot
        from src.config import Config, BuilderConfig

        # Create config
        config = Config(
            safe_address=creds["safe_address"],
            builder=BuilderConfig(
                api_key=creds["builder_key"],
                api_secret=creds["builder_secret"],
                api_passphrase=creds["builder_passphrase"],
            ) if creds["builder_key"] else BuilderConfig()
        )

        # Initialize bot
        bot = TradingBot(
            config=config,
            private_key=creds["private_key"]
        )

        print_success(f"Bot initialized: {bot.is_initialized()}")
        print_info(f"Signer: {bot.signer.address if bot.signer else 'None'}")
        print_info(f"CLOB Client: {bot.clob_client is not None}")
        print_info(f"Relayer Client: {bot.relayer_client is not None}")
        print_info(f"Gasless: {config.use_gasless}")

        # Test order dict creation
        order_dict = bot.create_order_dict(
            token_id="1234567890",
            price=0.65,
            size=10.0,
            side="BUY"
        )
        if order_dict["side"] == "BUY":
            print_success("Order dict creation successful")
        else:
            print_error("Order dict creation failed")
            return False

        return True

    except Exception as e:
        print_error(f"Bot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_client_module(creds: dict) -> bool:
    """Test the client module."""
    print_header("5. Testing Client Module (client.py)")

    try:
        from src.client import ClobClient
        from src.config import BuilderConfig

        builder_config = BuilderConfig(
            api_key=creds["builder_key"],
            api_secret=creds["builder_secret"],
            api_passphrase=creds["builder_passphrase"],
        ) if creds["builder_key"] else None

        # Create CLOB client
        clob = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,
            funder=creds["safe_address"],
            builder_creds=builder_config
        )

        print_success(f"CLOB Client created")
        print_info(f"Host: {clob.host}")
        print_info(f"Chain ID: {clob.chain_id}")

        # Test HMAC header generation
        if builder_config and builder_config.is_configured():
            headers = clob._build_headers("GET", "/orders")
            expected_keys = [
                "POLY_BUILDER_API_KEY",
                "POLY_BUILDER_TIMESTAMP",
                "POLY_BUILDER_PASSPHRASE",
                "POLY_BUILDER_SIGNATURE"
            ]
            if all(k in headers for k in expected_keys):
                print_success(f"HMAC headers generated: {list(headers.keys())}")
            else:
                print_error("Missing HMAC headers")
                return False
        else:
            print_warning("Builder not configured, skipping HMAC test")

        return True

    except Exception as e:
        print_error(f"Client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_workflow(creds: dict) -> bool:
    """Test complete file-based workflow."""
    print_header("6. Testing Complete File Workflow")

    try:
        from src.crypto import KeyManager
        from src.config import Config, BuilderConfig
        from src.bot import TradingBot

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "encrypted_key.json")
            config_file = os.path.join(tmpdir, "config.yaml")
            password = "secure_test_password"

            # 1. Encrypt and save key
            manager = KeyManager()
            manager.encrypt_and_save(creds["private_key"], password, key_file)
            print_success("Step 1: Encrypted key saved")

            # 2. Create and save config
            config = Config(
                safe_address=creds["safe_address"],
                builder=BuilderConfig(
                    api_key=creds["builder_key"],
                    api_secret=creds["builder_secret"],
                    api_passphrase=creds["builder_passphrase"],
                ) if creds["builder_key"] else BuilderConfig(),
                data_dir=tmpdir
            )
            config.save(config_file)
            print_success("Step 2: Config saved")

            # 3. Load config from file
            loaded_config = Config.load(config_file)
            print_success("Step 3: Config loaded")

            # 4. Initialize bot with encrypted key
            bot = TradingBot(
                config=loaded_config,
                encrypted_key_path=key_file,
                password=password
            )
            print_success("Step 4: Bot initialized with encrypted key")

            # Verify
            if bot.is_initialized() and bot.signer:
                print_success("Step 5: Bot fully operational")
                return True
            else:
                print_error("Bot not fully initialized")
                return False

    except Exception as e:
        print_error(f"File workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print_header("Polymarket Arbitrage Bot - Full Integration Test")

    # Get credentials
    creds = get_test_credentials()

    if not creds["private_key"]:
        print_error("POLY_PRIVATE_KEY environment variable not set!")
        print_info("Set it with: export POLY_PRIVATE_KEY=your_private_key")
        print_info("Or copy .env.example to .env and run: source .env")
        sys.exit(1)

    if not creds["safe_address"]:
        print_error("POLY_PROXY_WALLET environment variable not set!")
        print_info("Set it with: export POLY_PROXY_WALLET=0x...")
        sys.exit(1)

    print_info(f"Testing with address: {creds['safe_address']}")
    print_info(f"Builder configured: {bool(creds['builder_key'])}")

    # Run tests
    results = []

    results.append(("Crypto Module", test_crypto_module(creds["private_key"])))
    results.append(("Signer Module", test_signer_module(creds["private_key"], creds["safe_address"])))
    results.append(("Config Module", test_config_module(creds)))
    results.append(("Bot Module", test_bot_module(creds)))
    results.append(("Client Module", test_client_module(creds)))
    results.append(("File Workflow", test_file_workflow(creds)))

    # Summary
    print_header("Test Summary")

    passed = 0
    failed = 0

    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
            passed += 1
        else:
            print_error(f"{name}: FAILED")
            failed += 1

    print()
    print(f"{Colors.BOLD}Total: {passed} passed, {failed} failed{Colors.RESET}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed! ✗{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
