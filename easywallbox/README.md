# EasyWallbox Home Assistant Add-on

Control and monitor your Free2Move EasyWallbox directly from Home Assistant via Bluetooth and MQTT.

## Features

- **Bluetooth Low Energy (BLE)** connection to EasyWallbox.
- **MQTT Integration** for control and monitoring.
- **Dynamic Power Management (DPM)** control.
- **Charging Session** management (Start/Stop/Delay).
- **Automatic Reconnection** for both BLE and MQTT.
- **Home Assistant Add-on** ready.

## Installation

1.  **Add Repository**:
    - Go to **Settings** > **Add-ons** > **Add-on Store**.
    - Click the three dots in the top right corner > **Repositories**.
    - Add the URL of this repository: `https://github.com/Nawo/easywallbox`
    - Click **Add**.

2.  **Install Add-on**:
    - Find "EasyWallbox" in the store.
    - Click **Install**.

## Configuration

1.  **How to get PIN code**
    - Open your camera / QR Code reader and point it to the sticker. You will get something like:

    - BT:N:2911AA00101728;M:F2ME.EWE08APEFXX;D:eWB01728;P:001234;A:9844;;
    - Let's decode it:
    - N: Serial 2911AA00101728
    - M: Part Number F2ME.EWE08APEFXX
    - D: BT Name eWB01728
    - P: Device Pin 001234
    - A: BLE Pin 9844

    We need the A: value, in my case it's "9844"

2.  **How to get MAC address**
    - Go to terminal and use command `bluetoothctl`
    - Search device witch name is "eWB01728" or something similar
    - Copy mac address from the list
    - Close bluetoothctl with `exit` command 

3.  **Configure the add-on in the **Configuration** tab**

| Option | Description | Default |
| :--- | :--- | :--- |
| `wallbox_address` | **Required**. The MAC address of your Wallbox
| `wallbox_pin` | **Required**. The Bluetooth PIN code found on the sticker (A value). |
| `mqtt_host` | MQTT Broker hostname or IP. | `"core-mosquitto"` |
| `mqtt_port` | MQTT Broker port. | `1883` |
| `mqtt_username` | MQTT Username.
| `mqtt_password` | MQTT Password.
| `mqtt_topic` | Base MQTT topic. | `"easywallbox"` |

> **Note**: This add-on requires Bluetooth access. It uses the host's Bluetooth adapter (`hci0`).

## MQTT Topics

The add-on listens for commands and publishes status updates.

### Commands

Publish to these topics to control the Wallbox:

#### Dynamic Power Management (DPM)
- `easywallbox/dpm`:
    - `on`: Turn DPM ON.
    - `off`: Turn DPM OFF.
    - `limit`: Request current DPM limit.
    - `status`: Request DPM status.
    - `limit/{value}`: Set DPM limit (e.g., `easywallbox/dpm/limit/16`).

#### Charging
- `easywallbox/charge`:
    - `start`: Start charging immediately.
    - `stop`: Stop charging immediately.
    - `start/{delay}`: Start charging after `{delay}` hours.
    - `stop/{delay}`: Stop charging after `{delay}` hours.

#### Limits
- `easywallbox/limit`:
    - `dpm`: Get DPM limit.
    - `safe`: Get Safe limit.
    - `user`: Get User limit.
    - `dpm/{value}`: Set DPM limit.
    - `safe/{value}`: Set Safe limit.
    - `user/{value}`: Set User limit.

#### Read Data
- `easywallbox/read`:
    - `manufacturing`: Read manufacturing data.
    - `settings`: Read settings.
    - `app_data`: Read app data.
    - `hw_settings`: Read hardware settings.
    - `voltage`: Read supply voltage.

### Responses

All responses from the Wallbox are published to:
- `easywallbox/message`: Raw response data.

## Troubleshooting

### "No such file or directory" (BLE Error)
If you see `[Errno 2] No such file or directory` in the logs, it means the add-on cannot access the Bluetooth adapter. Ensure that the host system has a working Bluetooth adapter

### Connection Issues
- Ensure the Wallbox is within Bluetooth range.
- Verify the MAC address and PIN code.
- Check MQTT broker connection settings.

## License
MIT
