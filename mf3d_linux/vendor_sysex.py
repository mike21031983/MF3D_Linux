"""Read-only vendor SysEx envelope recognizer recovered from macOS Utility.
Never transmits SysEx, flash, reset, or persistent configuration commands.
"""
from dataclasses import dataclass
MANUFACTURER=(0x00,0x01,0x79)
@dataclass(frozen=True)
class ParsedSysEx:
    valid_vendor:bool
    category:str
    family_payload:tuple[int,...]
    data:tuple[int,...]
def parse_sysex(message):
    if hasattr(message,'type'):
        if message.type!='sysex':raise ValueError('Expected SysEx')
        raw=bytes(message.data)
    else:
        raw=bytes(message)
        if raw and raw[0]==0xF0:
            if raw[-1]!=0xF7:raise ValueError('Unterminated SysEx')
            raw=raw[1:-1]
    if not raw or len(raw)>8192 or any(b>=128 for b in raw):
        raise ValueError('Invalid SysEx data')
    if len(raw)<3 or tuple(raw[:3])!=MANUFACTURER:
        return ParsedSysEx(False,'other-manufacturer',(),tuple(raw))
    data=tuple(raw[3:])
    category='vendor-other'
    if len(data)>=2:
        if data[:2]==(2,1):category='serial-response'
        elif data[:2]==(4,0):category='bulk-response'
        elif data[:2]==(4,1):category='bulk-read-request'
    return ParsedSysEx(True,category,data,tuple(raw))
