"""MQTT to BLE command mapper for EasyWallbox.

This module provides a centralized mapping between MQTT topics/payloads
and Bluetooth Low Energy commands for the Wallbox.
"""
import logging
from typing import Optional, Dict, Any, Callable
from .bluetoothCommands import (
    setUserLimit, getUserLimit,
    setSafeLimit, getSafeLimit,
    setDpmLimit, getDpmLimit,
    setDpmLimit, getDpmLimit,
    startCharge, stopCharge,
    readSettings, readAppData,
    readManufacturing, readHwSettings, readSupplyVoltage
)

log = logging.getLogger(__name__)

# Declarative Mapping: Topic -> { Payload : BLE_Command or Function }
MQTT2BLE: Dict[str, Dict[str, Any]] = {
    "easywallbox/charge": {
        "start": startCharge(0),
        "start/": startCharge,  # Function reference
        "stop": stopCharge(0),
        "stop/": stopCharge,    # Function reference
    },
    "easywallbox/limit": {
        "dpm": getDpmLimit(),
        "dpm/": setDpmLimit,    # Function reference
        "safe": getSafeLimit(),
        "safe/": setSafeLimit,  # Function reference
        "user": getUserLimit(),
        "user/": setUserLimit,  # Function reference
    },
    "easywallbox/read": {
        "manufacturing": readManufacturing(),
        "settings": readSettings(),
        "app_data": readAppData(),
        "hw_settings": readHwSettings(),
        "voltage": readSupplyVoltage()
    },
}

class MQTTBLEMapper:
    """Maps MQTT topics and payloads to BLE commands using a declarative map."""
    
    @staticmethod
    def map_command(subtopic: str, payload: str) -> Optional[str]:
        """
        Map an MQTT topic and payload to a BLE command.
        """
        full_topic = f"easywallbox/{subtopic}"
        
        try:
            # 1. Check exact match in MQTT2BLE
            if full_topic in MQTT2BLE:
                topic_map = MQTT2BLE[full_topic]
                
                # A) Exact payload match (e.g. "on" -> setDpmOn())
                if payload in topic_map:
                    return topic_map[payload]
                
                # B) Dynamic payload with separator (e.g. "limit/16")
                # Check for keys ending with "/" which indicate function references
                # This handles cases where payload is just "16" but we match a key like "limit/"?
                # No, the user request implies payload is "limit/16" for legacy or just "16" for HA?
                # Let's support the user's explicit structure: "limit/" : setDpmLimit
                
                # C) Handle "cmd/val" payloads for legacy topics
                # e.g. topic="easywallbox/dpm", payload="limit/16"
                if "/" in payload:
                    cmd_part, val_part = payload.split("/", 1)
                    cmd_key = f"{cmd_part}/"
                    if cmd_key in topic_map:
                        func = topic_map[cmd_key]
                        if callable(func):
                            try:
                                return func(int(val_part))
                            except ValueError:
                                pass
                
            return None
            
        except Exception as e:
            log.warning(f"Error mapping MQTT to BLE: {e}")
            return None
    
    @staticmethod
    def needs_multiple_commands(subtopic: str, payload: str) -> bool:
        """Check if this command requires multiple BLE commands."""
        return subtopic == "read" and payload == "settings"
    
    @staticmethod
    def get_refresh_commands() -> list[str]:
        """Get all commands for refresh operation."""
        return [
            readSettings(),
            readAppData(),
            readManufacturing(),
            readHwSettings(),
            readSupplyVoltage(),
            getDpmLimit(),
            getSafeLimit(),
            getUserLimit()
        ]
