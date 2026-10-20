"""Conservative MF3D identity READ protocol recovered from vendor Mac Mach-O.

Original Device::requestDeviceId: F0 00 01 79 05 F7.
Device::sysExRouted receives 05 01 while an identity request is pending.
Offsets below match the original executable. Response layout and endianness
still await validation on physical hardware. No EEPROM/DFU/write.
"""
from dataclasses import dataclass
from .vendor_sysex import parse_sysex,MANUFACTURER
REQ=bytes((0xF0,*MANUFACTURER,0x05,0xF7))
EXPECTED_FAMILY=0x0003
EXPECTED_MODEL=0x0001

def identity_request()->bytes:
    return REQ

@dataclass(frozen=True)
class Identity:
    family:int
    model:int
    opaque_identifier:bytes
    firmware_bytes:bytes
    reply_body:bytes
    @property
    def is_standard_mf3d(self)->bool:
        return (self.family,self.model)==(EXPECTED_FAMILY,EXPECTED_MODEL)
    @property
    def family_code(self)->str:
        return f'{self.family:04X}'
    @property
    def model_number(self)->str:
        return f'{self.model:04X}'

def decode_identity_reply(message)->Identity|None:
    """Fail closed on short 05 01; no claim of cryptographic authenticity."""
    parsed=parse_sysex(message)
    if not parsed.valid_vendor:return None
    data=parsed.family_payload
    if len(data)<2 or data[:2]!=(5,1):return None
    # Original native code accesses offsets 8..11 despite only checking >=10.
    if len(data)<12 or len(data)>128:raise ValueError('Short/oversized identity reply')
    return Identity(
        family=int.from_bytes(bytes(data[4:6]),'little'),
        model=int.from_bytes(bytes(data[6:8]),'little'),
        opaque_identifier=bytes(data[2:10]),
        firmware_bytes=bytes(data[8:12]),
        reply_body=bytes(data),
    )
