#!/usr/bin/env python3

from bleak import BleakClient
import commands
# Zakładam, że utils.py istnieje i ma get_required_env
from easywallbox.utils import log

class EasyWallbox:

    def __init__(self, address, pin, mqtt_topic, mqtt_client):
        self.address = address
        self.pin = pin
        self.mqtt_topic = mqtt_topic
        self.mqtt_client = mqtt_client
        self.client = BleakClient(self.address)
        self.connected = False
        
    async def connect(self):
        log.info(f"BLE: Connecting to {self.address}...")
        try:
            await self.client.connect()
            self.connected = self.client.is_connected
            log.info(f"BLE: Connected status: {self.connected}")
            if self.connected:
                # Update status in HA
                self._publish_status("connected")
                return True
        except Exception as e:
            log.error(f"BLE: Connection failed: {e}")
            self._publish_status("disconnected")
            return False

    async def disconnect(self):
        if self.connected:
            log.info("BLE: Disconnecting...")
            await self.client.disconnect()
            self.connected = False
            self._publish_status("disconnected")

    async def setup_notifications(self):
        try:
            await self.client.start_notify(self.WALLBOX_TX, self._notification_handler_rx)
            await self.client.start_notify(self.WALLBOX_ST, self._notification_handler_st)
            log.info("BLE: Notifications started")
        except Exception as e:
            log.error(f"BLE: Failed to start notifications: {e}")

    async def write(self, data):
        if not self.connected:
            log.warning("BLE: Cannot write, not connected!")
            return

        if isinstance(data, str):
            data = bytearray(data, 'utf-8')
        
        log.info(f"BLE: Writing data: {data}")
        try:
            # response=False is safer for UART-like devices that don't ACK writes
            await self.client.write_gatt_char(self.WALLBOX_RX, data, response=False)
        except Exception as e:
            log.error(f"BLE: Write failed: {e}")

    async def authenticate(self):
        log.info(f"BLE: Authenticating with PIN {self.pin}...")
        # Using protocol authentication only (skipping system bonding)
        try:
            auth_cmd = commands.authBle(self.pin)
            await self.write(auth_cmd)
        except Exception as e:
            log.error(f"BLE: Auth failed: {e}")

    def _publish_status(self, status):
        if self.mqtt_client:
            self.mqtt_client.publish(f"{self.mqtt_topic}/connectivity", status, retain=True)

    def _notification_handler_rx(self, sender, data):
        decoded = data.decode('utf-8', errors='ignore')
        # Buffer logic can be added here if messages are fragmented
        # For simplicity, publishing raw chunk
        if self.mqtt_client:
             self.mqtt_client.publish(f"{self.mqtt_topic}/message", decoded, retain=False)

    def _notification_handler_st(self, sender, data):
        decoded = data.decode('utf-8', errors='ignore')
        log.info(f"BLE ST: {decoded}")
