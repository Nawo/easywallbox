"""Coordinator for EasyWallbox."""
import asyncio
import logging
from .config import Config
from .mqtt_manager import MQTTManager
from .ble_manager import BLEManager
from .mqtt_ble_mapper import MQTTBLEMapper

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
        if not topic.startswith(self._config.mqtt_topic):
            return
        
        subtopic = topic[len(self._config.mqtt_topic):].lstrip('/')
        
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
                
                # Read-after-write: verify actual state from Wallbox
                if subtopic.startswith("set/"):
                    await self._read_after_write(subtopic)
                    
            except Exception as e:
                log.error(f"Failed to forward to BLE: {e}")

    async def _read_after_write(self, subtopic: str):
        """Read actual value from Wallbox after writing."""
        cmd = subtopic[4:]  # Remove "set/"
        
        # Map write commands to their corresponding read commands
        read_command = None
        
        if cmd.endswith("_limit"):
            limit_type = cmd.replace("_limit", "")
            if limit_type == "user":
                read_command = WALLBOX_EPROM["GET_USER_LIMIT"]
            elif limit_type == "safe":
                read_command = WALLBOX_EPROM["GET_SAFE_LIMIT"]
            elif limit_type == "dpm":
                read_command = WALLBOX_EPROM["GET_DPM_LIMIT"]
        elif cmd == "dpm":
            read_command = WALLBOX_EPROM["GET_DPM_STATUS"]
        
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
            # $DPM,STATUS,0          (DPM OFF)
            # $DPM,STATUS,1          (DPM ON)
            
            if data.startswith("$EEP,READ,IDX,"):
                parts = data.split(",")
                if len(parts) >= 5:
                    idx = parts[3]
                    value = int(parts[4].strip())
                    
                    # Map index to entity
                    if idx == "174":  # User limit
                        await self._mqtt.publish("number/user_limit/state", str(value))
                    elif idx == "172":  # Safe limit
                        await self._mqtt.publish("number/safe_limit/state", str(value))
                    elif idx == "156":  # DPM limit (example, verify actual index)
                        await self._mqtt.publish("number/dpm_limit/state", str(value))
            
            elif data.startswith("$DPM,STATUS,"):
                parts = data.split(",")
                if len(parts) >= 3:
                    status = parts[2].strip()
                    state = "ON" if status == "1" else "OFF"
                    await self._mqtt.publish("switch/dpm/state", state)
        
        except Exception as e:
            log.warning(f"Failed to parse response: {e}")

    def stop(self):
        """Stop the coordinator."""
        self._mqtt.stop()
        self._ble.stop()
