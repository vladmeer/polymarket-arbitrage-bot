"""
Config Module - Configuration Management

Provides configuration loading and validation from YAML files
and environment variables.

Configuration Precedence (highest to lowest):
1. Environment variables
2. YAML config file
3. Default values

Environment Variables:
    POLY_PRIVATE_KEY: Private key (hex string, with or without 0x prefix)
    POLY_PROXY_WALLET: Polymarket Proxy wallet address
    POLY_RPC_URL: Polygon RPC URL
    POLY_BUILDER_API_KEY: Builder Program API key
    POLY_BUILDER_API_SECRET: Builder Program API secret
    POLY_BUILDER_API_PASSPHRASE: Builder Program passphrase
    POLY_CLOB_HOST: CLOB API host
    POLY_CHAIN_ID: Chain ID (default: 137)
    POLY_DATA_DIR: Data directory for credentials
    POLY_LOG_LEVEL: Logging level

Example:
    from src.config import Config

    # Load from environment variables
    config = Config.from_env()

    # Load from YAML with env override
    config = Config.load("config.yaml")
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field
from dataclasses import asdict
import yaml


# Environment variable prefix
ENV_PREFIX = "POLY_"


def get_env(name: str, default: str = "") -> str:
    """Get environment variable with prefix."""
    return os.environ.get(f"{ENV_PREFIX}{name}", default)


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    val = get_env(name, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def get_env_int(name: str, default: int = 0) -> int:
    """Get integer environment variable."""
    val = get_env(name, "")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def get_env_float(name: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    val = get_env(name, "")
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigNotFoundError(ConfigError):
    """Raised when config file is not found."""
    pass


@dataclass
class BuilderConfig:
    """Builder Program configuration for gasless transactions."""
    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""

    def is_configured(self) -> bool:
        """Check if Builder credentials are configured."""
        return bool(self.api_key and self.api_secret and self.api_passphrase)


@dataclass
class ClobConfig:
    """CLOB (Central Limit Order Book) configuration."""
    host: str = "https://clob.polymarket.com"
    chain_id: int = 137
    signature_type: int = 2  # Gnosis Safe

    def is_valid(self) -> bool:
        """Validate CLOB configuration."""
        return bool(self.host and self.host.startswith("http"))


@dataclass
class RelayerConfig:
    """Relayer configuration for gasless transactions."""
    host: str = "https://relayer-v2.polymarket.com"
    tx_type: str = "SAFE"  # SAFE or PROXY

    def is_configured(self) -> bool:
        """Check if relayer is configured."""
        return bool(self.host)


@dataclass
class Config:
    """
    Main configuration class for the trading bot.

    Attributes:
        safe_address: The Polymarket Safe/Proxy wallet address
        rpc_url: Polygon RPC URL for blockchain calls
        clob: CLOB API configuration
        relayer: Relayer configuration for gasless transactions
        builder: Builder Program credentials
        default_token_id: Default token ID for trading
        data_dir: Directory for storing credentials and data
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # Core settings
    safe_address: str = ""
    rpc_url: str = "https://polygon-rpc.com"

    # API configurations
    clob: ClobConfig = field(default_factory=ClobConfig)
    relayer: RelayerConfig = field(default_factory=RelayerConfig)
    builder: BuilderConfig = field(default_factory=BuilderConfig)

    # Trading defaults
    default_token_id: str = ""
    default_size: float = 1.0
    default_price: float = 0.5

    # Paths
    data_dir: str = "credentials"

    # Logging
    log_level: str = "INFO"

    # Auto-configure for gasless mode (auto-detected based on builder credentials)
    use_gasless: bool = False

    def __post_init__(self):
        """Validate and normalize configuration."""
        if self.safe_address:
            self.safe_address = self.safe_address.lower()
        # Auto-enable gasless if builder is configured
        if self.builder.is_configured():
            self.use_gasless = True

    @classmethod
    def load(cls, filepath: str = "config.yaml") -> "Config":
        """
        Load configuration from YAML file.

        Args:
            filepath: Path to YAML config file

        Returns:
            Config instance
        """
        path = Path(filepath)

        if not path.exists():
            raise ConfigNotFoundError(f"Config file not found: {filepath}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        # Core settings
        if "safe_address" in data:
            config.safe_address = data["safe_address"]
        if "rpc_url" in data:
            config.rpc_url = data["rpc_url"]

        # CLOB config
        if "clob" in data:
            clob_data = data["clob"]
            config.clob = ClobConfig(
                host=clob_data.get("host", config.clob.host),
                chain_id=clob_data.get("chain_id", config.clob.chain_id),
                signature_type=clob_data.get("signature_type", config.clob.signature_type),
            )

        # Relayer config
        if "relayer" in data:
            relayer_data = data["relayer"]
            config.relayer = RelayerConfig(
                host=relayer_data.get("host", config.relayer.host),
                tx_type=relayer_data.get("tx_type", config.relayer.tx_type),
            )

        # Builder config
        if "builder" in data:
            builder_data = data["builder"]
            config.builder = BuilderConfig(
                api_key=builder_data.get("api_key", ""),
                api_secret=builder_data.get("api_secret", ""),
                api_passphrase=builder_data.get("api_passphrase", ""),
            )

        # Trading defaults
        if "default_token_id" in data:
            config.default_token_id = data["default_token_id"]
        if "default_size" in data:
            config.default_size = float(data["default_size"])
        if "default_price" in data:
            config.default_price = float(data["default_price"])

        # Paths
        if "data_dir" in data:
            config.data_dir = data["data_dir"]

        # Logging
        if "log_level" in data:
            config.log_level = data["log_level"]

        # Auto-detect gasless mode
        config.use_gasless = config.builder.is_configured()

        return config

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Environment variables (all prefixed with POLY_):
            PRIVATE_KEY: Private key (stored separately, not in config)
            PROXY_WALLET: Polymarket Proxy wallet address
            RPC_URL: Polygon RPC URL
            BUILDER_API_KEY: Builder Program API key
            BUILDER_API_SECRET: Builder Program API secret
            BUILDER_API_PASSPHRASE: Builder Program passphrase
            CLOB_HOST: CLOB API host
            CHAIN_ID: Chain ID (default: 137)
            DATA_DIR: Data directory for credentials
            LOG_LEVEL: Logging level

        Returns:
            Config instance
        """
        config = cls()

        # Core settings
        safe_address = get_env("PROXY_WALLET")
        if safe_address:
            config.safe_address = safe_address

        rpc_url = get_env("RPC_URL")
        if rpc_url:
            config.rpc_url = rpc_url

        # Builder credentials
        api_key = get_env("BUILDER_API_KEY")
        api_secret = get_env("BUILDER_API_SECRET")
        api_passphrase = get_env("BUILDER_API_PASSPHRASE")
        if api_key or api_secret or api_passphrase:
            config.builder = BuilderConfig(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            )

        # CLOB config
        clob_host = get_env("CLOB_HOST")
        chain_id = get_env_int("CHAIN_ID", 137)
        if clob_host:
            config.clob = ClobConfig(
                host=clob_host,
                chain_id=chain_id,
            )
        elif chain_id != 137:
            config.clob.chain_id = chain_id

        # Other settings
        data_dir = get_env("DATA_DIR")
        if data_dir:
            config.data_dir = data_dir

        log_level = get_env("LOG_LEVEL")
        if log_level:
            config.log_level = log_level.upper()

        default_size = get_env_float("DEFAULT_SIZE")
        if default_size:
            config.default_size = default_size

        default_price = get_env_float("DEFAULT_PRICE")
        if default_price:
            config.default_price = default_price

        # Auto-detect gasless mode
        config.use_gasless = config.builder.is_configured()

        return config

    @classmethod
    def load_with_env(cls, filepath: str = "config.yaml") -> "Config":
        """
        Load configuration from YAML file with environment variable overrides.

        Args:
            filepath: Path to YAML config file

        Returns:
            Config instance with env vars taking precedence
        """
        # Start with YAML config if it exists
        path = Path(filepath)
        if path.exists():
            config = cls.load(filepath)
        else:
            config = cls()

        # Override with environment variables
        safe_address = get_env("PROXY_WALLET")
        if safe_address:
            config.safe_address = safe_address.lower()

        rpc_url = get_env("RPC_URL")
        if rpc_url:
            config.rpc_url = rpc_url

        # Builder credentials from env override YAML
        api_key = get_env("BUILDER_API_KEY")
        api_secret = get_env("BUILDER_API_SECRET")
        api_passphrase = get_env("BUILDER_API_PASSPHRASE")
        if api_key:
            config.builder.api_key = api_key
        if api_secret:
            config.builder.api_secret = api_secret
        if api_passphrase:
            config.builder.api_passphrase = api_passphrase

        # Other settings
        data_dir = get_env("DATA_DIR")
        if data_dir:
            config.data_dir = data_dir

        log_level = get_env("LOG_LEVEL")
        if log_level:
            config.log_level = log_level.upper()

        # Re-check gasless mode
        config.use_gasless = config.builder.is_configured()

        return config

    def save(self, filepath: str = "config.yaml") -> None:
        """Save configuration to YAML file."""
        data = self.to_dict()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "safe_address": self.safe_address,
            "rpc_url": self.rpc_url,
            "clob": asdict(self.clob),
            "relayer": asdict(self.relayer),
            "builder": asdict(self.builder),
            "default_token_id": self.default_token_id,
            "default_size": self.default_size,
            "default_price": self.default_price,
            "data_dir": self.data_dir,
            "log_level": self.log_level,
        }

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.safe_address:
            errors.append("safe_address is required")

        if not self.rpc_url:
            errors.append("rpc_url is required")

        if not self.clob.is_valid():
            errors.append("clob configuration is invalid")

        if self.use_gasless and not self.builder.is_configured():
            errors.append("gasless mode enabled but builder credentials not configured")

        return errors

    def get_credential_path(self, name: str) -> Path:
        """Get path for credential file."""
        return Path(self.data_dir) / name

    def get_encrypted_key_path(self) -> Path:
        """Get path for encrypted private key file."""
        return self.get_credential_path("encrypted_key.json")

    def get_api_creds_path(self) -> Path:
        """Get path for API credentials file."""
        return self.get_credential_path("api_creds.json")

    def __repr__(self) -> str:
        """String representation."""
        gasless_status = "enabled" if self.use_gasless else "disabled"
        return (
            f"Config(safe_address={self.safe_address[:10]}..., "
            f"gasless={gasless_status}, "
            f"data_dir={self.data_dir})"
        )
