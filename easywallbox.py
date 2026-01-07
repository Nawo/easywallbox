#!/usr/bin/env python3
import asyncio
import sys
from bleak import BleakClient
import paho.mqtt.client as mqtt
import os
import commands
import mqttmap
import time
import random
import logging

FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

mqttClient = None

def get_required_env(key):
    """Get a required environment variable or exit if not set."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        log.error(f"CRITICAL ERROR: Missing required environment variable: {key}")
        sys.exit(1)
    return value

class EasyWallbox:
    WALLBOX_RX = "a9da6040-0823-4995-94ec-9ce41ca28833"
    WALLBOX_SERVICE = "331a36f5-2459-45ea-9d95-6142f0c4b307"
    WALLBOX_ST = "75A9F022-AF03-4E41-B4BC-9DE90A47D50B"
    WALLBOX_TX = "a73e9a10-628f-4494-a099-12efaf72258f"
    WALLBOX_UUID ="0A8C44F5-F80D-8141-6618-2564F1881650"

    mqtt_topic = get_required_env('MQTT_TOPIC')

    def __init__(self, queue, address, pin):
        self.WALLBOX_ADDRESS = address
        self.WALLBOX_PIN = pin
        self._client = BleakClient(self.WALLBOX_ADDRESS)
        self._queue = queue

    def is_connected(self):
        return self._client.is_connected()

    async def write(self, data):
        if isinstance(data, str):
            data = bytearray(data, 'utf-8')
        await self._client.write_gatt_char(self.WALLBOX_RX, data)
        log.info("ble write: %s", data)

    async def connect(self):
        log.info(f"Connecting BLE to {self.WALLBOX_ADDRESS}...")
        try:
            await self._client.connect()
            log.info(f"Connected: {self._client.is_connected}")
        except Exception as e:
            log.error(f"Failed to connect to Wallbox: {e}")
            sys.exit(1)

    async def pair(self):
        log.info("Pairing BLE...")
        paired = sys.platform == "darwin" or await self._client.pair(protection_level=2)
        log.info(f"Paired: {paired}")
        log.info("Skipping system pairing (protocol auth only).")
        return True

    async def start_notify(self):
        await self._client.start_notify(self.WALLBOX_TX, self._notification_handler_rx)
        log.info("TX NOTIFY STARTED")
        await self._client.start_notify(self.WALLBOX_ST, self._notification_handler_st)
        log.info("ST NOTIFY STARTED")

    _notification_buffer_rx = ""
    def _notification_handler_rx(self, sender, data):
        global client
        self._notification_buffer_rx += data.decode()
        if "\n" in self._notification_buffer_rx:
            log.info("_notification RX received: %s", self._notification_buffer_rx)

            if (client):
                client.publish(topic=mqtt_topic+"/message", payload=self._notification_buffer_rx, qos=1, retain=False)
            self._notification_buffer_rx = ""

    _notification_buffer_st = ""
    def _notification_handler_st(self, sender, data):
        self._notification_buffer_st += data.decode()
        if "\n" in self._notification_buffer_st:
            log.info("_notification ST received: %s", self._notification_buffer_st)
            self._notification_buffer_st = ""

async def main():
    global client
    
    log.info("--- Starting EasyWallbox Controller ---")

    wb_address = get_required_env('WALLBOX_ADDRESS')
    wb_pin = get_required_env('WALLBOX_PIN')
    mqtt_host = get_required_env('MQTT_HOST')
    mqtt_topic = get_required_env('MQTT_TOPIC')
    
    try:
        mqtt_port = int(get_required_env('MQTT_PORT'))
    except ValueError:
        log.error("CRITICAL ERROR: MQTT_PORT must be an integer!")
        sys.exit(1)

    mqtt_username = get_required_env('MQTT_USERNAME')
    mqtt_password = get_required_env('MQTT_PASSWORD')

    log.info(f"Configuration loaded. Wallbox: {wb_address}, MQTT: {mqtt_host}:{mqtt_port}")

    queue = asyncio.Queue()

    eb = EasyWallbox(queue, wb_address, wb_pin)
    
    await eb.connect()
    #await eb.pair()
    await eb.start_notify()

    log.info("BLE AUTH START with PIN: %s", eb.WALLBOX_PIN)
    await eb.write(commands.authBle(eb.WALLBOX_PIN))

    # MQTT Callbacks
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.connected_flag = True
            log.info("Connected to MQTT Broker!")
            client.subscribe([(mqtt_topic+"/dpm",0), (mqtt_topic+"/charge",0), (mqtt_topic+"/limit",0), (mqtt_topic+"/read", 0)])
        else:
            log.error(f"Failed to connect to MQTT, return code {rc}")

    def on_message(client, userdata, msg):
        topic = msg.topic
        try:
            message = msg.payload.decode()
        except:
            message = str(msg.payload)
            
        log.info(f"Message received [{topic}]: {message}")
        ble_command = None

        try:
            if "/" in message:
                msx = message.split("/") 
                if topic in mqttmap.MQTT2BLE and (msx[0]+"/") in mqttmap.MQTT2BLE[topic]:
                    ble_command = mqttmap.MQTT2BLE[topic][msx[0]+"/"](msx[1])
            else:
                if topic in mqttmap.MQTT2BLE and message in mqttmap.MQTT2BLE[topic]:
                    ble_command = mqttmap.MQTT2BLE[topic][message]
        except Exception as e:
            log.warning(f"Error parsing MQTT message: {e}")
            pass

        if ble_command:
            queue.put_nowait(ble_command)


    mqtt.Client.connected_flag = False
    
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "mqtt_easywallbox")
    except AttributeError:
        client = mqtt.Client("mqtt_easywallbox")

    client.on_connect = on_connect
    client.on_message = on_message
    
    if mqtt_username and mqtt_password:
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
    
    try:
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()
    except Exception as e:
        log.error(f"Could not connect to MQTT Broker: {e}")
        sys.exit(1)

    wait_count = 0
    while not client.connected_flag:
        log.info("Waiting for MQTT connection...")
        time.sleep(1)
        wait_count += 1
        if wait_count > 30:
            log.error("MQTT Connection timeout. Exiting.")
            sys.exit(1)
    
    while True:
        if not queue.empty():
            item = queue.get_nowait()
            if item is None:
                break
            log.info(f"Sending BLE command: {item.hex() if isinstance(item, (bytes, bytearray)) else item}")
            try:
                await eb.write(item)
            except Exception as e:
                log.error(f"Error writing to BLE: {e}")
        await asyncio.sleep(0.1)

try:
    asyncio.run(main())
except asyncio.CancelledError:
    pass
except KeyboardInterrupt:
    log.info("Stopping...")
    sys.exit(0)
except Exception as e:
    log.error(f"Fatal error: {e}")
    sys.exit(1)