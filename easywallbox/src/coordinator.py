"""Coordinator for EasyWallbox."""
import asyncio
import logging
from .config import Config
from .mqtt_manager import MQTTManager
from .ble_manager import BLEManager
from .const import WALLBOX_EPROM, WALLBOX_COMMANDS, WALLBOX_BLE

log = logging.getLogger(__name__)

class Coordinator:
    def __init__(self, config: Config):
        self._config = config
        self._mqtt = MQTTManager(config, self._on_mqtt_message)
        self._ble = BLEManager(config, self._on_ble_notify)
        self._last_data = ""

    async def start(self):
        """Start the coordinator and managers."""
        log.info("Starting Coordinator...")
        
        # Run both managers concurrently
        await asyncio.gather(
            self._mqtt.start(),
            self._ble.start()
        )

    async def _on_mqtt_message(self, topic: str, payload: str):
        """Handle incoming MQTT messages."""
        log.info(f"Coordinator received MQTT: {topic} -> {payload}")
        
        # Determine relative topic
        # topic is full topic e.g. "easywallbox/charge"
        # we want "charge"
        if not topic.startswith(self._config.mqtt_topic):
            return
        
        subtopic = topic[len(self._config.mqtt_topic):].lstrip('/')
        
        command = self._map_mqtt_to_ble(subtopic, payload)
        if command:
            log.info(f"Forwarding to BLE: {command.strip()}")
            try:
                await self._ble.write(command)
            except Exception as e:
                log.error(f"Failed to forward to BLE: {e}")

    def get_status(self):
        """Get current status for dashboard."""
        return {
            "ble_connected": self._ble._client.is_connected if self._ble._client else False,
            "mqtt_connected": self._mqtt._client is not None, # Simplified check
            "last_data": self._last_data
        }

    async def reconnect_ble(self):
        """Force BLE reconnect."""
        # This is a bit hacky, ideally BLEManager handles this
        if self._ble._client:
            await self._ble._client.disconnect()

    async def set_limit(self, limit_type: str, value: str):
        """Set limit via BLE."""
        cmd = None
        val = int(float(value))
        if limit_type == "dpm":
            cmd = WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(val))
        elif limit_type == "safe":
            cmd = WALLBOX_EPROM["SET_SAFE_LIMIT"].format(limit=str(val))
        elif limit_type == "user":
            cmd = WALLBOX_EPROM["SET_USER_LIMIT"].format(limit=str(val))
            
        if cmd:
            await self._ble.write(cmd)

    async def refresh_data(self):
        """Request fresh data."""
        await self._ble.write(WALLBOX_EPROM["READ_SETTINGS"])
        await self._ble.write(WALLBOX_EPROM["READ_APP_DATA"])

    async def _on_ble_notify(self, data: str):
        """Handle incoming BLE notifications."""
        log.info(f"Coordinator received BLE notify: {data.strip()}")
        self._last_data = data.strip() # Store last data
        # Forward to MQTT
        await self._mqtt.publish("message", data)

    def _map_mqtt_to_ble(self, subtopic: str, payload: str) -> str | None:
        """Map MQTT topic and payload to BLE command."""
        try:
            # Logic ported from mqttmap.py
            
            # /dpm
            if subtopic == "dpm":
                if payload == "on": return WALLBOX_EPROM["SET_DPM_ON"]
                if payload == "off": return WALLBOX_EPROM["SET_DPM_OFF"]
                if payload == "limit": return WALLBOX_EPROM["GET_DPM_LIMIT"]
                if payload == "status": return WALLBOX_EPROM["GET_DPM_STATUS"]
                # Handle "limit/X" format if payload contains slash? 
                # Original code handled split on payload if it contained "/"
                if "/" in payload:
                    cmd, val = payload.split("/", 1)
                    if cmd == "limit":
                        return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(int(val)*10))

            # /charge
            elif subtopic == "charge":
                if payload == "start": return WALLBOX_COMMANDS["START_CHARGE"].format(delay=0)
                if payload == "stop": return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=0)
                if "/" in payload:
                    cmd, val = payload.split("/", 1)
                    if cmd == "start": return WALLBOX_COMMANDS["START_CHARGE"].format(delay=val)
                    if cmd == "stop": return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=val)

            # /limit
            elif subtopic == "limit":
                if payload == "dpm": return WALLBOX_EPROM["GET_DPM_LIMIT"]
                if payload == "safe": return WALLBOX_EPROM["GET_SAFE_LIMIT"]
                if payload == "user": return WALLBOX_EPROM["GET_USER_LIMIT"]
                if "/" in payload:
                    cmd, val = payload.split("/", 1)
                    if cmd == "dpm": return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(int(val)))
                    if cmd == "safe": return WALLBOX_EPROM["SET_SAFE_LIMIT"].format(limit=str(int(val)))
                    if cmd == "user": return WALLBOX_EPROM["SET_USER_LIMIT"].format(limit=str(int(val)))

            # /read
            elif subtopic == "read":
                if payload == "manufacturing": return WALLBOX_EPROM["READ_MANUFACTURING"]
                if payload == "settings": return WALLBOX_EPROM["READ_SETTINGS"]
                if payload == "app_data": return WALLBOX_EPROM["READ_APP_DATA"]
                if payload == "hw_settings": return WALLBOX_EPROM["READ_HW_SETTINGS"]
                if payload == "voltage": return WALLBOX_EPROM["READ_SUPPLY_VOLTAGE"]

        except Exception as e:
            log.warning(f"Error mapping MQTT to BLE: {e}")
        
        return None

    def stop(self):
        """Stop the coordinator."""
        self._mqtt.stop()
        self._ble.stop()
