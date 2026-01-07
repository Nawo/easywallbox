
#!/usr/bin/env python3

import asyncio
from asyncio import log
import os
import sys
import traceback
from easywallbox import ha_dashboard, mqttmap
from easywallbox.easywallbox import EasyWallbox
import paho.mqtt.client as mqtt

from easywallbox.utils import get_required_env


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
            ha_dashboard.publish_discovery(c, mqtt_topic, wb_address)
            
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