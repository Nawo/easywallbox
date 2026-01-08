"""Main entry point for EasyWallbox."""
import asyncio
import logging
import sys
import signal
from .config import load_config
from .coordinator import Coordinator

# Logging configuration
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT, level=logging.INFO)
log = logging.getLogger(__name__)

async def main():
    """Main function."""
    log.info("--- Starting EasyWallbox Controller ---")
    
    try:
        config = load_config()
    except Exception as e:
        log.critical(f"Failed to load configuration: {e}")
        sys.exit(1)

    coordinator = Coordinator(config)

    # Handle signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        log.info("Signal received, stopping...")
        stop_event.set()
        coordinator.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start coordinator
    coordinator_task = asyncio.create_task(coordinator.start())

    # Wait for stop signal
    await stop_event.wait()
    
    # Wait for coordinator to finish (if it returns)
    # In this design, coordinator.start() runs forever until stopped
    # We can cancel it or wait for it to exit if it handles stop() gracefully
    try:
        await asyncio.wait_for(coordinator_task, timeout=5.0)
    except asyncio.TimeoutError:
        log.warning("Coordinator did not stop in time, cancelling...")
        coordinator_task.cancel()
    except asyncio.CancelledError:
        pass
    
    log.info("EasyWallbox Controller stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
