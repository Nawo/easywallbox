import os
import sys
from easywallbox.easywallbox import log

def get_required_env(key):
    """Get a required environment variable or exit if not set."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        log.error(f"CRITICAL ERROR: Missing required environment variable: {key}")
        sys.exit(1)
    return value