"""BLE Manager for EasyWallbox."""
import asyncio
import logging
from bleak import BleakClient, BleakError
from typing import Callable, Optional
from .config import Config
from .const import (
    WALLBOX_RX, WALLBOX_TX, WALLBOX_ST, 
    WALLBOX_BLE, WALLBOX_ANSWERS
)

log = logging.getLogger(__name__)

class BLEManager:
    def __init__(self, config: Config, on_notify_callback: Callable[[str], None], on_connection_change_callback: Optional[Callable[[bool], None]] = None):
        self._config = config
        self._on_notify_callback = on_notify_callback
        self._on_connection_change_callback = on_connection_change_callback
        self._client: Optional[BleakClient] = None
        self._running = False
        self._notification_buffer_rx = ""
        self._notification_buffer_st = ""

    async def start(self):
        """Start the BLE connection loop."""
        self._running = True
        while self._running:
            try:
                log.info(f"Connecting to Wallbox at {self._config.wallbox_address}...")
                self._client = BleakClient(self._config.wallbox_address)
                
                await self._client.connect()
                log.info(f"Connected to Wallbox: {self._client.is_connected}")

                # Start Notifications BEFORE auth to receive auth response
                await self._client.start_notify(WALLBOX_TX, self._notification_handler_rx)
                log.info("TX NOTIFY STARTED")
                await self._client.start_notify(WALLBOX_ST, self._notification_handler_st)
                log.info("ST NOTIFY STARTED")

                # Protocol Authentication
                await self._authenticate()
                
                # Give authentication time to process (Wallbox may send response)
                await asyncio.sleep(2)
                
                # Mark as online only after successful authentication
                if self._on_connection_change_callback:
                    await self._on_connection_change_callback(True)

                # Monitor connection
                while self._running and self._client.is_connected:
                    await asyncio.sleep(1)

            except BleakError as e:
                log.error(f"BLE Connection error: {e}")
            except Exception as e:
                log.error(f"Unexpected BLE error: {e}")
            finally:
                if self._on_connection_change_callback:
                    await self._on_connection_change_callback(False)
                    
                if self._client and self._client.is_connected:
                    try:
                        await self._client.disconnect()
                    except:
                        pass
                self._client = None
                
                if self._running:
                    log.info("Waiting 5 seconds before reconnecting BLE...")
                    await asyncio.sleep(5)

    async def _authenticate(self):
        """Perform protocol-level authentication."""
        log.info(f"Authenticating with PIN: {self._config.wallbox_pin}")
        auth_cmd = WALLBOX_BLE["LOGIN"].format(pin=self._config.wallbox_pin)
        await self.write(auth_cmd)

    async def write(self, data: str | bytes):
        """Write data to the Wallbox."""
        if not self._client or not self._client.is_connected:
            log.warning("Cannot write to BLE: Not connected")
            return

        if isinstance(data, str):
            data = bytearray(data, 'utf-8')
        
        try:
            log.debug(f"Writing to BLE: {data}")
            await self._client.write_gatt_char(WALLBOX_RX, data, response=False)
        except Exception as e:
            log.error(f"BLE Write Failed: {e}")
            raise

    def _notification_handler_rx(self, sender, data):
        """Handle RX notifications."""
        try:
            self._notification_buffer_rx += data.decode('utf-8')
        except UnicodeDecodeError as e:
            log.error(f"Failed to decode BLE data: {e}")
            self._notification_buffer_rx = ""  # Discard corrupt data
            return
        
        if "\n" in self._notification_buffer_rx:
            log.debug(f"RX Notification: {self._notification_buffer_rx.strip()}")
            if self._on_notify_callback:
                # Schedule async callback and track exceptions
                task = asyncio.create_task(self._on_notify_callback(self._notification_buffer_rx))
                task.add_done_callback(self._handle_callback_exception)
            self._notification_buffer_rx = ""
    
    def _handle_callback_exception(self, task):
        """Handle exceptions from notification callbacks."""
        try:
            task.result()
        except Exception as e:
            log.error(f"Error in notification callback: {e}", exc_info=True)

    def _notification_handler_st(self, sender, data):
        """Handle ST notifications."""
        try:
            self._notification_buffer_st += data.decode('utf-8')
        except UnicodeDecodeError as e:
            log.error(f"Failed to decode ST data: {e}")
            self._notification_buffer_st = ""
            return
        
        if "\n" in self._notification_buffer_st:
            log.debug(f"ST Notification: {self._notification_buffer_st.strip()}")
            # Currently we don't do anything with ST notifications other than log
            # But we could forward them if needed.
            self._notification_buffer_st = ""

    def stop(self):
        """Stop the BLE manager."""
        self._running = False
