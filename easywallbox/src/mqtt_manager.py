"""MQTT Manager for EasyWallbox."""
import asyncio
import logging
import aiomqtt
from typing import Callable, Optional, List, Tuple
from .config import Config

log = logging.getLogger(__name__)

class MQTTManager:
    def __init__(self, config: Config, on_message_callback: Callable[[str, str], None]):
        self._config = config
        self._on_message_callback = on_message_callback
        self._client: Optional[aiomqtt.Client] = None
        self._running = False

    async def start(self):
        """Start the MQTT client loop."""
        self._running = True
        while self._running:
            try:
                log.info(f"Connecting to MQTT Broker at {self._config.mqtt_host}:{self._config.mqtt_port}...")
                async with aiomqtt.Client(
                    hostname=self._config.mqtt_host,
                    port=self._config.mqtt_port,
                    username=self._config.mqtt_username,
                    password=self._config.mqtt_password,
                ) as client:
                    self._client = client
                    log.info("Connected to MQTT Broker!")
                    
                    # Publish Discovery Config
                    await self.publish_discovery()
                    
                    # Subscribe to topics
                    topics = [
                        f"{self._config.mqtt_topic}/dpm",
                        f"{self._config.mqtt_topic}/charge",
                        f"{self._config.mqtt_topic}/limit",
                        f"{self._config.mqtt_topic}/read",
                        f"{self._config.mqtt_topic}/set/#", # Listen for HA commands
                    ]
                    for topic in topics:
                        await client.subscribe(topic)
                        log.info(f"Subscribed to: {topic}")

                    # Message loop
                    async for message in client.messages:
                        topic = message.topic.value
                        payload = message.payload.decode() if isinstance(message.payload, bytes) else str(message.payload)
                        log.debug(f"MQTT Received [{topic}]: {payload}")
                        
                        try:
                            if self._on_message_callback:
                                await self._on_message_callback(topic, payload)
                        except Exception as e:
                            log.error(f"Error processing MQTT message: {e}")

            except aiomqtt.MqttError as e:
                log.error(f"MQTT Connection error: {e}")
                self._client = None
                await asyncio.sleep(5) # Wait before reconnecting
            except Exception as e:
                log.error(f"Unexpected MQTT error: {e}")
                self._client = None
                await asyncio.sleep(5)

    async def publish_discovery(self):
        """Publish Home Assistant MQTT Discovery payloads."""
        if not self._client: return
        
        device_info = {
            "identifiers": [self._config.wallbox_address],
            "name": "EasyWallbox",
            "manufacturer": "Free2Move",
            "model": "EasyWallbox",
        }
        
        base_topic = self._config.mqtt_topic
        
        # Helper to publish config
        async def pub_config(component, object_id, config):
            topic = f"homeassistant/{component}/easywallbox/{object_id}/config"
            import json
            await self._client.publish(topic, json.dumps(config), retain=True)

        # 1. Connectivity (Binary Sensor)
        await pub_config("binary_sensor", "connectivity", {
            "name": "Connectivity",
            "device_class": "connectivity",
            "state_topic": f"{base_topic}/sensor/connectivity/state",
            "unique_id": f"easywallbox_{self._config.wallbox_address}_connectivity",
            "device": device_info
        })

        # 2. DPM Switch
        await pub_config("switch", "dpm", {
            "name": "DPM",
            "icon": "mdi:flash-auto",
            "state_topic": f"{base_topic}/switch/dpm/state",
            "command_topic": f"{base_topic}/set/dpm",
            "unique_id": f"easywallbox_{self._config.wallbox_address}_dpm",
            "device": device_info
        })

        # 3. Limits (Numbers)
        for limit in ["dpm", "safe", "user"]:
            await pub_config("number", f"{limit}_limit", {
                "name": f"{limit.upper()} Limit",
                "icon": "mdi:current-ac",
                "state_topic": f"{base_topic}/number/{limit}_limit/state",
                "command_topic": f"{base_topic}/set/{limit}_limit",
                "min": 0,
                "max": 7.2,
                "step": 0.1,
                "unit_of_measurement": "A",
                "unique_id": f"easywallbox_{self._config.wallbox_address}_{limit}_limit",
                "device": device_info
            })

        # 4. Refresh Button
        await pub_config("button", "refresh", {
            "name": "Refresh Data",
            "icon": "mdi:refresh",
            "command_topic": f"{base_topic}/set/refresh",
            "unique_id": f"easywallbox_{self._config.wallbox_address}_refresh",
            "device": device_info
        })
        
        log.info("Published MQTT Discovery configs")


    async def publish(self, subtopic: str, payload: str):
        """Publish a message to MQTT."""
        if self._client:
            full_topic = f"{self._config.mqtt_topic}/{subtopic}"
            try:
                await self._client.publish(full_topic, payload)
                log.debug(f"Published to {full_topic}: {payload}")
            except Exception as e:
                log.error(f"Failed to publish to {full_topic}: {e}")
        else:
            log.warning("Cannot publish: MQTT client not connected")

    def stop(self):
        """Stop the MQTT loop."""
        self._running = False
