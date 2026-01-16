#!/usr/bin/with-contenv bashio

export WALLBOX_ADDRESS=$(bashio::config 'wallbox_address')
export WALLBOX_PIN=$(bashio::config 'wallbox_pin')
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USERNAME=$(bashio::config 'mqtt_username')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')

echo "Starting EasyWallbox..."
python3 -m src.main
