# EasyWallbox Home Assistant Add-on

Control and monitor your Free2Move EasyWallbox directly from Home Assistant via Bluetooth and MQTT.

## Features

- **Bluetooth Low Energy (BLE)** connection to EasyWallbox.
- **MQTT Integration** for control and monitoring.
- **Dynamic Power Management (DPM)** control.
- **Charging Session** management (Start/Stop/Delay).
- **Automatic Reconnection** for both BLE and MQTT.
- **Home Assistant Add-on** ready.
- **MQTT Auto-Discovery** - automatic entity creation in Home Assistant.
- **Availability Tracking** - entities disabled when connection lost.

## Architecture & Information Flow

The add-on consists of several modular components:

```
Home Assistant UI
       ↓ (MQTT Discovery)
    MQTT Broker
       ↓ (easywallbox/set/*)
  MQTTManager ←→ Coordinator ←→ BLEManager
       ↓              ↓              ↓
  (publish)    (mqtt_ble_mapper)  (Bleak)
                                    ↓
                               Wallbox (BLE)
```

### Component Roles

1. **BLEManager** (`ble_manager.py`):
   - Manages Bluetooth Low Energy connection to the Wallbox
   - Handles authentication and auto-reconnection (every 5s on failure)
   - Listens for notifications from the Wallbox
   - Notifies Coordinator of connection state changes

2. **MQTTManager** (`mqtt_manager.py`):
   - Connects to MQTT broker
   - Publishes Home Assistant Discovery configs on startup
   - Subscribes to command topics
   - Forwards MQTT messages to Coordinator

3. **MQTTBLEMapper** (`mqtt_ble_mapper.py`):
   - **Central mapping table** for all MQTT → BLE commands
   - Supports both Home Assistant Discovery topics (`set/*`) and legacy topics
   - Example: `set/user_limit` + `"16"` → `$EEP,WRITE,IDX,174,16\n`

4. **Coordinator** (`coordinator.py`):
   - **Orchestrates** communication between MQTT and BLE
   - Routes MQTT commands → Mapper → BLE
   - Routes BLE notifications → MQTT
   - Manages availability state (`online`/`offline`)

### Data Flow Examples

#### Setting a Limit (Home Assistant → Wallbox)
```
1. User slides "User Limit" to 16A in HA UI
2. HA publishes: easywallbox/set/user_limit → "16"
3. MQTTManager receives message → Coordinator
4. Coordinator calls Mapper.map_command("set/user_limit", "16")
5. Mapper returns: "$EEP,WRITE,IDX,174,16\n"
6. Coordinator sends to BLEManager
7. BLEManager writes to Wallbox via Bluetooth
8. Coordinator publishes optimistic state: easywallbox/number/user_limit/state → "16"
```

#### Receiving Data (Wallbox → Home Assistant)
```
1. Wallbox sends BLE notification (e.g., voltage reading)
2. BLEManager receives → calls Coordinator._on_ble_notify()
3. Coordinator publishes to: easywallbox/message
4. Home Assistant receives and displays in MQTT integration
```

#### Availability Tracking
```
1. BLEManager connects → calls Coordinator._on_ble_connection_change(True)
2. Coordinator publishes: easywallbox/availability → "online"
3. HA marks all entities as available (controls enabled)
---
1. BLE disconnects → calls Coordinator._on_ble_connection_change(False)
2. Coordinator publishes: easywallbox/availability → "offline"
3. HA marks all entities as unavailable (controls greyed out)
```


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
