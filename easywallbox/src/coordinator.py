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
                
                # Optimistic state update for HA Discovery commands
                if subtopic.startswith("set/"):
                    await self._publish_state_update(subtopic, payload)
                    
            except Exception as e:
                log.error(f"Failed to forward to BLE: {e}")

    async def _publish_state_update(self, subtopic: str, payload: str):
        """Publish optimistic state updates for HA Discovery commands."""
        cmd = subtopic[4:]  # Remove "set/"
        
        if cmd == "dpm":
            await self._mqtt.publish("switch/dpm/state", payload)
        elif cmd.endswith("_limit"):
            await self._mqtt.publish(f"number/{cmd}/state", payload)

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
        
        # Forward to MQTT
        await self._mqtt.publish("message", data)

    def stop(self):
        """Stop the coordinator."""
        self._mqtt.stop()
        self._ble.stop()
