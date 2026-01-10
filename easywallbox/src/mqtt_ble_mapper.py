"""MQTT to BLE command mapper for EasyWallbox.

This module provides a centralized mapping between MQTT topics/payloads
and Bluetooth Low Energy commands for the Wallbox.
"""
import logging
from typing import Optional
from .const import WALLBOX_EPROM, WALLBOX_COMMANDS

log = logging.getLogger(__name__)


class MQTTBLEMapper:
    """Maps MQTT topics and payloads to BLE commands."""
    
    @staticmethod
    def map_command(subtopic: str, payload: str) -> Optional[str]:
        """
        Map an MQTT topic and payload to a BLE command.
        
        Args:
            subtopic: The MQTT topic relative to the base (e.g., "set/user_limit")
            payload: The MQTT message payload (e.g., "16" or "ON")
            
        Returns:
            The BLE command string to send, or None if mapping fails
        """
        try:
            # Home Assistant Discovery Commands (set/*)
            if subtopic.startswith("set/"):
                return MQTTBLEMapper._map_ha_command(subtopic[4:], payload)
            
            # Legacy MQTT Topics
            return MQTTBLEMapper._map_legacy_command(subtopic, payload)
            
        except Exception as e:
            log.warning(f"Error mapping MQTT to BLE: {e}")
            return None
    
    @staticmethod
    def _map_ha_command(command: str, payload: str) -> Optional[str]:
        """Map Home Assistant Discovery commands (set/*)."""
        
        # DPM Switch: set/dpm → ON/OFF
        if command == "dpm":
            if payload == "ON":
                return WALLBOX_EPROM["SET_DPM_ON"]
            elif payload == "OFF":
                return WALLBOX_EPROM["SET_DPM_OFF"]
        
        # Limits: set/user_limit → value
        elif command.endswith("_limit"):
            limit_type = command.replace("_limit", "")  # user, safe, dpm
            val = int(float(payload))
            
            if limit_type == "user":
                return WALLBOX_EPROM["SET_USER_LIMIT"].format(limit=str(val))
            elif limit_type == "safe":
                return WALLBOX_EPROM["SET_SAFE_LIMIT"].format(limit=str(val))
            elif limit_type == "dpm":
                return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(val))
        
        # Refresh: set/refresh → READ commands
        elif command == "refresh":
            # Return first command; caller should send both
            return WALLBOX_EPROM["READ_SETTINGS"]
        
        # Charging Control
        elif command == "start_charge":
            return WALLBOX_COMMANDS["START_CHARGE"].format(delay=0)
        elif command == "stop_charge":
            return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=0)
        
        return None
    
    @staticmethod
    def _map_legacy_command(subtopic: str, payload: str) -> Optional[str]:
        """Map legacy MQTT topics for backward compatibility."""
        
        # /dpm
        if subtopic == "dpm":
            if payload == "on":
                return WALLBOX_EPROM["SET_DPM_ON"]
            elif payload == "off":
                return WALLBOX_EPROM["SET_DPM_OFF"]
            elif payload == "limit":
                return WALLBOX_EPROM["GET_DPM_LIMIT"]
            elif payload == "status":
                return WALLBOX_EPROM["GET_DPM_STATUS"]
            elif "/" in payload:
                cmd, val = payload.split("/", 1)
                if cmd == "limit":
                    return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(int(val)))
        
        # /charge
        elif subtopic == "charge":
            if payload == "start":
                return WALLBOX_COMMANDS["START_CHARGE"].format(delay=0)
            elif payload == "stop":
                return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=0)
            elif "/" in payload:
                cmd, val = payload.split("/", 1)
                if cmd == "start":
                    return WALLBOX_COMMANDS["START_CHARGE"].format(delay=val)
                elif cmd == "stop":
                    return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=val)
        
        # /limit
        elif subtopic == "limit":
            if payload == "dpm":
                return WALLBOX_EPROM["GET_DPM_LIMIT"]
            elif payload == "safe":
                return WALLBOX_EPROM["GET_SAFE_LIMIT"]
            elif payload == "user":
                return WALLBOX_EPROM["GET_USER_LIMIT"]
            elif "/" in payload:
                cmd, val = payload.split("/", 1)
                value = str(int(val))
                if cmd == "dpm":
                    return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=value)
                elif cmd == "safe":
                    return WALLBOX_EPROM["SET_SAFE_LIMIT"].format(limit=value)
                elif cmd == "user":
                    return WALLBOX_EPROM["SET_USER_LIMIT"].format(limit=value)
        
        # /read
        elif subtopic == "read":
            if payload == "manufacturing":
                return WALLBOX_EPROM["READ_MANUFACTURING"]
            elif payload == "settings":
                return WALLBOX_EPROM["READ_SETTINGS"]
            elif payload == "app_data":
                return WALLBOX_EPROM["READ_APP_DATA"]
            elif payload == "hw_settings":
                return WALLBOX_EPROM["READ_HW_SETTINGS"]
            elif payload == "voltage":
                return WALLBOX_EPROM["READ_SUPPLY_VOLTAGE"]
        
        return None
    
    @staticmethod
    def needs_multiple_commands(subtopic: str, payload: str) -> bool:
        """Check if this command requires multiple BLE commands."""
        return subtopic == "set/refresh"
    
    @staticmethod
    def get_refresh_commands() -> list[str]:
        """Get all commands for refresh operation."""
        return [
            WALLBOX_EPROM["READ_SETTINGS"],
            WALLBOX_EPROM["READ_APP_DATA"]
        ]
