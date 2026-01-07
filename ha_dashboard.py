from asyncio import log
import json


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
