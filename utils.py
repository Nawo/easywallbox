import logging
import os
import sys

# --- CONFIGURATION ---
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

WALLBOX_RX = "a9da6040-0823-4995-94ec-9ce41ca28833"
WALLBOX_SERVICE = "331a36f5-2459-45ea-9d95-6142f0c4b307"
WALLBOX_ST = "75A9F022-AF03-4E41-B4BC-9DE90A47D50B"
WALLBOX_TX = "a73e9a10-628f-4494-a099-12efaf72258f"

def get_required_env(key):
    """Get a required environment variable or exit if not set."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        log.error(f"CRITICAL ERROR: Missing required environment variable: {key}")
        sys.exit(1)
    return value