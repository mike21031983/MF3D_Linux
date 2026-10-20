"""Read-only MF3D SysEx bulk protocol, recovered from the original Mac Utility.

Static proof: ConfigWidget::pullBulkTransfer at 0x100108d90 creates
F0 00 01 79 04 01 <tag> F7.
Callback ConfigWidget::sysEx 0x100104820 accepts 04 00 replies:
tag, two termination-marker fields, one opaque field, then 7-bit data.
Do not automatically send any request. NO EEPROM writes / DFU / reset.
"""
from dataclasses import dataclass,field
from .vendor_sysex import parse_sysex,MANUFACTURER
VALID_COLOR_TAGS=(1,2)
EXPECTED_COLOR_SIZE=192
MAX_FRAME_VALUES=128
MAX_FRAMES=64

def build_bulk_read_request(tag:int)->bytes:
    if type(tag) is not int or tag not in VALID_COLOR_TAGS:
        raise ValueError('Only MF3D color block tags 1/2 are supported')
    return bytes((0xF0,*MANUFACTURER,4,1,tag,0xF7))

@dataclass(frozen=True)
class BulkReplyFrame:
    tag:int
    marker_a:int
    marker_b:int
    opaque:int
    values:tuple[int,...]
    @property
    def final_marker(self):
        return self.marker_a==self.marker_b

def decode_bulk_reply(message)->BulkReplyFrame|None:
    parsed=parse_sysex(message)
    if not parsed.valid_vendor or parsed.category!='bulk-response':
        return None
    p=parsed.family_payload
    if len(p)<7:raise ValueError('Bulk reply too short')
    _,_,tag,a,b,opaque,*values=p
    if not 0<=tag<=127 or len(values)>MAX_FRAME_VALUES:
        raise ValueError('Invalid tag or excessive payload')
    return BulkReplyFrame(tag,a,b,opaque,tuple(values))

@dataclass
class ColorBulkCapture:
    tag:int
    received:list[int]=field(default_factory=list)
    packets:list[BulkReplyFrame]=field(default_factory=list)
    complete:bool=False
    error:str|None=None
    def __post_init__(self):
        if type(self.tag) is not int or self.tag not in VALID_COLOR_TAGS:
            raise ValueError('Invalid color block')
    def feed(self,message)->bool:
        if self.complete or self.error:raise RuntimeError('Session ended')
        try:frame=decode_bulk_reply(message)
        except ValueError as e:
            self.error=str(e);raise
        if frame is None or frame.tag!=self.tag:return False
        if len(self.packets)>=MAX_FRAMES or len(self.received)+len(frame.values)>EXPECTED_COLOR_SIZE:
            self.error='Bulk response exceeds bounds'
            raise ValueError(self.error)
        self.packets.append(frame);self.received.extend(frame.values)
        if frame.final_marker:
            if len(self.received)!=EXPECTED_COLOR_SIZE:
                self.error=f'Final marker with {len(self.received)} values, expected 192'
                raise ValueError(self.error)
            self.complete=True
        return True
    def get_values(self):
        if not self.complete:raise RuntimeError('Capture incomplete')
        return tuple(self.received)
