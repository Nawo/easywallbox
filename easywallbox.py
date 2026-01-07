#!/usr/bin/env python3
import asyncio
import sys
import traceback
import json
import os
import logging
from bleak import BleakClient, BleakError
import paho.mqtt.client as mqtt
import commands
import mqttmap


def get_required_env(key):
    """Get a required environment variable or exit if not set."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        log.error(f"CRITICAL ERROR: Missing required environment variable: {key}")
        sys.exit(1)
    return value

# --- CONFIGURATION ---
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

class EasyWallbox:
    # UUIDs
    WALLBOX_RX = "a9da6040-0823-4995-94ec-9ce41ca28833"
    WALLBOX_SERVICE = "331a36f5-2459-45ea-9d95-6142f0c4b307"
    WALLBOX_ST = "75A9F022-AF03-4E41-B4BC-9DE90A47D50B"
    WALLBOX_TX = "a73e9a10-628f-4494-a099-12efaf72258f"
    
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

# --- MQTT DISCOVERY FUNCTION (The Community Feature) ---
def publish_discovery(client, topic, mac):
    """
    Sends Home Assistant MQTT Discovery payloads to automatically create the dashboard.
    """
    log.info("Sending Home Assistant Discovery Config...")
    
    device_info = {
        "identifiers": [mac],
        "name": "EasyWallbox",
        "manufacturer": "Free2Move",
        "model": "eSolutions"
    }
    
    clean_mac = mac.replace(":", "").lower()
    base_topic = f"homeassistant"

    # 1. Switch: Charge Start/Stop
    config_charge = {
        "name": "Charging",
        "unique_id": f"ewb_{clean_mac}_charge",
        "command_topic": f"{topic}/charge",
        "payload_on": "start",
        "payload_off": "stop",
        "icon": "mdi:ev-station",
        "device": device_info
    }
    client.publish(f"{base_topic}/switch/ewb_{clean_mac}/charge/config", json.dumps(config_charge), retain=True)

    # 2. Number: User Limit (Amps)
    config_limit = {
        "name": "User Current Limit",
        "unique_id": f"ewb_{clean_mac}_limit",
        "command_topic": f"{topic}/limit/user/",
        "min": 6, "max": 32, "step": 1,
        "unit_of_measurement": "A",
        "mode": "slider",
        "icon": "mdi:current-ac",
        "device": device_info
    }
    client.publish(f"{base_topic}/number/ewb_{clean_mac}/limit/config", json.dumps(config_limit), retain=True)

    # 3. Switch: DPM On/Off
    config_dpm_sw = {
        "name": "DPM Mode",
        "unique_id": f"ewb_{clean_mac}_dpm_sw",
        "command_topic": f"{topic}/dpm",
        "payload_on": "on",
        "payload_off": "off",
        "icon": "mdi:battery-charging-wireless",
        "device": device_info
    }
    client.publish(f"{base_topic}/switch/ewb_{clean_mac}/dpm_sw/config", json.dumps(config_dpm_sw), retain=True)

    # 4. Number: DPM Limit
    config_dpm_lim = {
        "name": "DPM Limit",
        "unique_id": f"ewb_{clean_mac}_dpm_lim",
        "command_topic": f"{topic}/dpm/limit/",
        "min": 0, "max": 32, "step": 1,
        "unit_of_measurement": "A",
        "mode": "box",
        "icon": "mdi:speedometer",
        "device": device_info
    }
    client.publish(f"{base_topic}/number/ewb_{clean_mac}/dpm_lim/config", json.dumps(config_dpm_lim), retain=True)

    # 5. Button: Reconnect (Physical action requested)
    config_reconnect = {
        "name": "Force Reconnect",
        "unique_id": f"ewb_{clean_mac}_reconnect",
        "command_topic": f"{topic}/control",
        "payload_press": "reconnect",
        "icon": "mdi:bluetooth-connect",
        "device": device_info
    }
    client.publish(f"{base_topic}/button/ewb_{clean_mac}/reconnect/config", json.dumps(config_reconnect), retain=True)

    # 6. Button: Read Settings
    config_read = {
        "name": "Read Settings",
        "unique_id": f"ewb_{clean_mac}_read_set",
        "command_topic": f"{topic}/read",
        "payload_press": "settings",
        "icon": "mdi:eye-refresh",
        "device": device_info
    }
    client.publish(f"{base_topic}/button/ewb_{clean_mac}/read_set/config", json.dumps(config_read), retain=True)
    
    # 7. Sensor: Connectivity Status
    config_status = {
        "name": "Connection Status",
        "unique_id": f"ewb_{clean_mac}_status",
        "state_topic": f"{topic}/connectivity",
        "icon": "mdi:bluetooth",
        "device": device_info
    }
    client.publish(f"{base_topic}/sensor/ewb_{clean_mac}/status/config", json.dumps(config_status), retain=True)

    log.info("Discovery Config Sent!")


# --- MAIN LOGIC ---

async def ble_task_loop(queue, eb, reconnect_event):
    """
    Manages the BLE connection lifecycle and sending commands from queue.
    Runs in parallel with MQTT.
    """
    while True:
        # 1. Connection Phase
        if not eb.connected:
            connected = await eb.connect()
            if connected:
                await eb.setup_notifications()
                await asyncio.sleep(1) # stabilize
                await eb.authenticate()
            else:
                log.warning("BLE: Connection failed, retrying in 10s...")
                await asyncio.sleep(10)
                continue

        # 2. Command Processing Phase (While connected)
        try:
            # Wait for a command from MQTT queue or a reconnect signal
            # We use wait_for to allow periodic health checks if needed
            try:
                # Check for forced reconnect
                if reconnect_event.is_set():
                    raise Exception("Forced Reconnect Requested")

                item = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # SPECIAL INTERNAL COMMANDS
                if item == "__RECONNECT__":
                    reconnect_event.clear()
                    await eb.disconnect()
                    await asyncio.sleep(2)
                    continue

                # NORMAL BLE COMMANDS
                await eb.write(item)
                queue.task_done()
            
            except asyncio.TimeoutError:
                pass # No command, loop again to check connection status
            
        except Exception as e:
            log.error(f"BLE Loop Error: {e}")
            await eb.disconnect()
            await asyncio.sleep(5) # Cool down before reconnect

async def main():
    log.info("--- EasyWallbox Controller Starting ---")

    # ENV Variables
    wb_address = get_required_env('WALLBOX_ADDRESS')
    wb_pin = get_required_env('WALLBOX_PIN')
    mqtt_host = get_required_env('MQTT_HOST')
    mqtt_topic = get_required_env('MQTT_TOPIC')
    mqtt_port = int(get_required_env('MQTT_PORT'))
    mqtt_username = os.getenv('MQTT_USERNAME', "")
    mqtt_password = os.getenv('MQTT_PASSWORD', "")

    # Queue for commands from MQTT -> BLE
    cmd_queue = asyncio.Queue()
    reconnect_event = asyncio.Event()

    # --- MQTT SETUP ---
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "ewb_addon")
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            log.info("MQTT: Connected!")
            # Send Auto-Discovery Config
            publish_discovery(c, mqtt_topic, wb_address)
            
            # Subscribe to all subtopics defined in mqttmap
            c.subscribe(f"{mqtt_topic}/#")
            c.publish(f"{mqtt_topic}/connectivity", "disconnected", retain=True) # Init status
        else:
            log.error(f"MQTT: Connection failed rc={rc}")

    def on_message(c, userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode()
        except:
            payload = str(msg.payload)
        
        log.info(f"MQTT RX: {topic} -> {payload}")

        # HANDLE PHYSICAL BUTTON (RECONNECT)
        if topic == f"{mqtt_topic}/control" and payload == "reconnect":
            log.info("COMMAND: FORCE RECONNECT RECEIVED")
            cmd_queue.put_nowait("__RECONNECT__")
            return

        # HANDLE MAPPING VIA MQTTMAP
        # Logic to find the command in the nested dictionary
        try:
            ble_command = None
            
            # Check for direct matches or split matches (like limit/10)
            # This logic mimics your original code but adapted
            if topic in mqttmap.MQTT2BLE:
                handler = mqttmap.MQTT2BLE[topic]
                
                # Case 1: Payload is a direct key (e.g., "start", "on", "settings")
                if payload in handler:
                    ble_command = handler[payload]
                
                # Case 2: Dynamic value (assuming the topic was subbed generally)
                # Note: MQTT wildcards might be better, but sticking to your map structure:
                # If topic ends in something that expects a value, handle it.
                # However, your map uses keys like "limit/" for dynamic setters.
                # We need to see if we can match keys.
                else:
                    # Iterate keys to find dynamic setters (ending in /)
                    for key, func in handler.items():
                        if key.endswith("/") and callable(func):
                             # Only if the payload is a number (simple validation)
                             if payload.isdigit():
                                 ble_command = func(payload)
                                 break
            
            if ble_command:
                cmd_queue.put_nowait(ble_command)
            else:
                log.debug(f"No mapping found for {topic} : {payload}")

        except Exception as e:
            log.error(f"Mapping Error: {e}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start() # Run MQTT in background thread
    except Exception as e:
        log.error(f"MQTT Fatal: {e}")
        sys.exit(1)

    # --- BLE SETUP ---
    eb = EasyWallbox(wb_address, wb_pin, mqtt_topic, client)

    # --- RUN LOOP ---
    try:
        # Run the BLE manager. MQTT is already running in loop_start() thread.
        await ble_task_loop(cmd_queue, eb, reconnect_event)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error("Critical Main Loop Error:")
        traceback.print_exc()
    finally:
        await eb.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)