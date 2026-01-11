"""Coordinator for EasyWallbox."""
import asyncio
import logging
from .config import Config
from .mqtt_manager import MQTTManager
from .ble_manager import BLEManager
from .mqtt_ble_mapper import MQTTBLEMapper
from .bluetoothCommands import (
    getUserLimit, getSafeLimit
)

log = logging.getLogger(__name__)

class Coordinator:
    def __init__(self, config: Config):
        self._config = config
        self._mqtt = MQTTManager(config, self._on_mqtt_message)
        self._ble = BLEManager(config, self._on_ble_notify, self._on_ble_connection_change)
        self._last_data = ""
        self._mapper = MQTTBLEMapper()

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
        log.debug(f"Coordinator received MQTT: {topic} -> {payload}")
        
        # Extract subtopic
        base_topic = "easywallbox"
        if not topic.startswith(base_topic):
            return
        
        subtopic = topic[len(base_topic):].lstrip('/')
        
        # Map MQTT to BLE command
        command = self._mapper.map_command(subtopic, payload)
        
        if command:
            log.info(f"Forwarding to BLE: {command.strip()}")
            try:
                await self._ble.write(command)
                
                # Handle refresh (requires multiple commands)
                if self._mapper.needs_multiple_commands(subtopic, payload):
                    for cmd in self._mapper.get_refresh_commands()[1:]:  # Skip first (already sent)
                        await self._ble.write(cmd)
                
                # Optimistic state update / Read-after-write
                # We want to read back values for limits
                if subtopic == "limit":
                    await self._read_after_write(subtopic, payload)
                    
            except Exception as e:
                log.error(f"Failed to forward to BLE: {e}")

    async def _read_after_write(self, subtopic: str, payload: str):
        """Read actual value from Wallbox after writing."""
        read_command = None
        
        if subtopic == "limit":
            if payload.startswith("user/"):
                read_command = getUserLimit()
            elif payload.startswith("safe/"):
                read_command = getSafeLimit()
        
        if read_command:
            log.info(f"Reading back state: {read_command.strip()}")
            await self._ble.write(read_command)

    async def _on_ble_connection_change(self, connected: bool):
        """Handle BLE connection state changes."""
        state = "online" if connected else "offline"
        log.info(f"BLE Connection State Changed: {state}")
        
        # Publish availability
        await self._mqtt.publish("availability", state)
        await self._mqtt.publish("sensor/connectivity/state", "ON" if connected else "OFF")

    async def _on_ble_notify(self, data: str):
        """Handle incoming BLE notifications."""
        log.info(f"Coordinator received BLE notify: {data.strip()}")
        self._last_data = data.strip()
        
        # Parse response and update HA states
        await self._parse_and_update_state(data.strip())
        
        # Forward raw data to MQTT
        await self._mqtt.publish("message", data)
    
    async def _parse_and_update_state(self, data: str):
        """Parse Wallbox response and update Home Assistant entity states."""
        try:
            # Example responses:
            # $EEP,READ,IDX,174,160  (User limit = 16.0A)
            # $EEP,READ,IDX,172,320  (Safe limit = 32.0A)
            
            # NOTE: EPROM indices below should be verified from actual Wallbox logs
            # Check easywallbox/message topic for real responses
            
            if data.startswith("$EEP,READ,IDX,"):
                parts = data.split(",")
                if len(parts) >= 5:
                    idx = parts[3]
                    value = int(parts[4].strip())
                    
                    # Map index to entity
                    if idx == "174":  # User limit
                        await self._mqtt.publish("number/user_limit/state", str(value))
                    elif idx == "156":  # Safe limit
                        await self._mqtt.publish("number/safe_limit/state", str(value))
        
        except Exception as e:
            log.warning(f"Failed to parse response: {e}")

    def stop(self):
        """Stop the coordinator."""
        self._mqtt.stop()
        self._ble.stop()
