"""Original Device::requestConfig, Mach-O 0x10010d8d0: read-only 02 00."""
from .vendor_sysex import MANUFACTURER
def build_main_config_read_request():
    """F0 00 01 79 02 00 F7; no write/reset/flash bytes."""
    return bytes((0xF0,*MANUFACTURER,0x02,0x00,0xF7))
