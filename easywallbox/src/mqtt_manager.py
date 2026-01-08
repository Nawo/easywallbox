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
                    
                    # Subscribe to topics
                    topics = [
                        f"{self._config.mqtt_topic}/dpm",
                        f"{self._config.mqtt_topic}/charge",
                        f"{self._config.mqtt_topic}/limit",
                        f"{self._config.mqtt_topic}/read",
                    ]
                    for topic in topics:
                        await client.subscribe(topic)
                        log.info(f"Subscribed to: {topic}")

                    # Message loop
                    async for message in client.messages:
                        topic = message.topic.value
                        payload = message.payload.decode() if isinstance(message.payload, bytes) else str(message.payload)
                        log.debug(f"MQTT Received [{topic}]: {payload}")
                        
                        # Dispatch to callback (fire and forget or await?)
                        # We'll run it in the loop to ensure order, but catch exceptions
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
