"""Constants for EasyWallbox."""

# BLE UUIDs
WALLBOX_RX = "a9da6040-0823-4995-94ec-9ce41ca28833"
WALLBOX_SERVICE = "331a36f5-2459-45ea-9d95-6142f0c4b307"
WALLBOX_ST = "75A9F022-AF03-4E41-B4BC-9DE90A47D50B"
WALLBOX_TX = "a73e9a10-628f-4494-a099-12efaf72258f"
WALLBOX_UUID = "0A8C44F5-F80D-8141-6618-2564F1881650"

# Protocol Constants
WALLBOX_ANSWERS = { 
    "ANSWER_ERRAUTH" : "$ERR,AUTH\n", 
    "ANSWER_ERRBUSY" : "$ERR,BUSY\n", 
    "ANSWER_SYNTAX" : "$ERR,SYNTAX\n", 
    "ANSWER_AUTHFAIL" : "$BLE,AUTH,FAIL\n", 
    "ANSWER_AUTHOK" : "$BLE,AUTH,OK\n", 
    "ANSWER_WRITE_FAIL" : "$EEP,WRITE,FAIL\n", 
    "ANSWER_LOGOUT" : "$BLE,LOGOUT,OK\n" 
}

WALLBOX_BLE = { 
    "LOGIN" : "$BLE,AUTH,{pin}\n", 
    "LOGOUT" : "$BLE,LOGOUT\n" 
}

WALLBOX_COMMANDS = { 
    "START_CHARGE" : "$CMD,CHARGE,START,{delay}\n", 
    "STOP_CHARGE" : "$CMD,CHARGE,STOP,{delay}\n" 
}

WALLBOX_EPROM = { 
    "INDEX_WRITE" : "$EEP,WRITE,IDX\n",
    "INDEX_READ" : "$EEP,READ,IDX\n",
    "READ_ALARMS" : "$EEP,READ,AL\n",
    "READ_MANUFACTURING" : "$EEP,READ,MF\n",
    "READ_SESSIONS" : "$EEP,READ,SL\n",
    "READ_SETTINGS" : "$EEP,READ,ST\n",
    "READ_APP_DATA" : "$DATA,READ,AD\n",
    "READ_HW_SETTINGS" : "$DATA,READ,HS\n",
    "READ_SUPPLY_VOLTAGE" : "$DATA,READ,SV\n",

    "SET_USER_LIMIT" : "$EEP,WRITE,IDX,174,{limit}\n",
    "SET_DPM_LIMIT" : "$EEP,WRITE,IDX,158,{limit}\n",
    "SET_SAFE_LIMIT" : "$EEP,WRITE,IDX,156,{limit}\n",
    "SET_DPM_OFF" : "$EEP,WRITE,IDX,178,0\n",
    "SET_DPM_ON" : "$EEP,WRITE,IDX,178,1\n",

    "GET_USER_LIMIT" : "$EEP,READ,IDX,174\n",
    "GET_DPM_LIMIT" : "$EEP,READ,IDX,158\n",
    "GET_SAFE_LIMIT" : "$EEP,READ,IDX,156\n",
    "GET_DPM_STATUS" : "$EEP,READ,IDX,178\n"
}

# ============================================================================
# Wrapper Functions for Commands
# ============================================================================

# EPROM Commands - Limits
def setUserLimit(value: int) -> str:
    """Set user current limit."""
    return WALLBOX_EPROM["SET_USER_LIMIT"].format(limit=str(value))

def getUserLimit() -> str:
    """Get user current limit."""
    return WALLBOX_EPROM["GET_USER_LIMIT"]

def setSafeLimit(value: int) -> str:
    """Set safe current limit."""
    return WALLBOX_EPROM["SET_SAFE_LIMIT"].format(limit=str(value))

def getSafeLimit() -> str:
    """Get safe current limit."""
    return WALLBOX_EPROM["GET_SAFE_LIMIT"]

def setDpmLimit(value: int) -> str:
    """Set DPM limit."""
    return WALLBOX_EPROM["SET_DPM_LIMIT"].format(limit=str(value))

def getDpmLimit() -> str:
    """Get DPM limit."""
    return WALLBOX_EPROM["GET_DPM_LIMIT"]

# EPROM Commands - DPM Control
def setDpmOn() -> str:
    """Enable Dynamic Power Management."""
    return WALLBOX_EPROM["SET_DPM_ON"]

def setDpmOff() -> str:
    """Disable Dynamic Power Management."""
    return WALLBOX_EPROM["SET_DPM_OFF"]

def getDpmStatus() -> str:
    """Get DPM status."""
    return WALLBOX_EPROM["GET_DPM_STATUS"]

# EPROM Commands - Read Data
def readManufacturing() -> str:
    """Read manufacturing data."""
    return WALLBOX_EPROM["READ_MANUFACTURING"]

def readSettings() -> str:
    """Read settings."""
    return WALLBOX_EPROM["READ_SETTINGS"]

def readAppData() -> str:
    """Read application data."""
    return WALLBOX_EPROM["READ_APP_DATA"]

def readHwSettings() -> str:
    """Read hardware settings."""
    return WALLBOX_EPROM["READ_HW_SETTINGS"]

def readSupplyVoltage() -> str:
    """Read supply voltage."""
    return WALLBOX_EPROM["READ_SUPPLY_VOLTAGE"]

# Charge Commands
def startCharge(delay: int = 0) -> str:
    """Start charging."""
    return WALLBOX_COMMANDS["START_CHARGE"].format(delay=delay)

def stopCharge(delay: int = 0) -> str:
    """Stop charging."""
    return WALLBOX_COMMANDS["STOP_CHARGE"].format(delay=delay)

# BLE Authentication
def login(pin: str) -> str:
    """Authenticate with Wallbox."""
    return WALLBOX_BLE["LOGIN"].format(pin=pin)

