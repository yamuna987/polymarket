#!/usr/bin/env python3
"""
Configuration Loader
Load and validate configuration from YAML file
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    # Load environment variables
    load_dotenv()

    # Load YAML config
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Replace environment variable references
    config = _replace_env_vars(config)

    # Validate configuration
    _validate_config(config)

    logger.info(f"Configuration loaded from {config_path}")

    return config


def _replace_env_vars(config: Any) -> Any:
    """
    Recursively replace ${ENV_VAR} references with environment variables

    Args:
        config: Configuration dict or value

    Returns:
        Configuration with env vars replaced
    """
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        # Extract env var name
        env_var = config[2:-1]
        value = os.getenv(env_var)
        if value is None:
            logger.warning(f"Environment variable not set: {env_var}")
            return ""
        return value
    else:
        return config


def _validate_config(config: Dict[str, Any]):
    """
    Validate configuration has required fields

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ["filters", "signal_detection", "discord", "api", "database"]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Validate API URLs
    api_config = config.get("api", {})
    required_urls = ["clob_url", "gamma_url", "data_url", "websocket_url"]

    for url_key in required_urls:
        if not api_config.get(url_key):
            raise ValueError(f"Missing required API URL: {url_key}")

    # Validate database config
    db_config = config.get("database", {})
    if db_config.get("type") not in ["sqlite", "postgresql"]:
        raise ValueError("Database type must be 'sqlite' or 'postgresql'")

    logger.info("Configuration validated successfully")


def get_database_url(config: Dict[str, Any]) -> str:
    """
    Get database URL from configuration

    Args:
        config: Configuration dictionary

    Returns:
        SQLAlchemy database URL
    """
    db_config = config.get("database", {})
    db_type = db_config.get("type", "sqlite")

    if db_type == "sqlite":
        db_path = db_config.get("sqlite_path", "database/signals.db")
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

    elif db_type == "postgresql":
        postgres_url = db_config.get("postgres_url") or os.getenv("DATABASE_URL")
        if not postgres_url:
            raise ValueError("PostgreSQL URL not configured")
        return postgres_url

    else:
        raise ValueError(f"Unsupported database type: {db_type}")
