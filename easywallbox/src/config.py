"""Configuration module for EasyWallbox."""
import os
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class Config:
    wallbox_address: str
    wallbox_pin: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_password: str

def get_required_env(key: str) -> str:
    """Get a required environment variable or raise ValueError."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {key}")
    return value

def load_config() -> Config:
    """Load configuration from environment variables."""
    try:
        config = Config(
            wallbox_address=get_required_env('WALLBOX_ADDRESS'),
            wallbox_pin=get_required_env('WALLBOX_PIN'),
            mqtt_host=get_required_env('MQTT_HOST'),
            mqtt_port=int(get_required_env('MQTT_PORT')),
            mqtt_username=get_required_env('MQTT_USERNAME'),
            mqtt_password=get_required_env('MQTT_PASSWORD'),
        )
        log.info("Configuration loaded successfully")
        return config
    except ValueError as e:
        log.critical(f"Configuration error: {e}")
        raise
