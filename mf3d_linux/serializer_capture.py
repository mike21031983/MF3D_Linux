"""Read-only vendor settings responses + offline .mfs serializer inspector.

Original ConfigWidget::sysEx @0x100104979 CLEARs MidiSerializer before
processing a NORMAL 02 01 SysEx (unless import flag at 0xa8 is set).
Therefore subsequent on-wire replies REPLACE a snapshot: never union
different frames to claim a whole hardware profile. No MIDI transmission.
"""
from dataclasses import dataclass,field
from pathlib import Path
import json
from .vendor_sysex import parse_sysex
from .device_profile import BY_KEY

MAX_FRAMES=64
MAX_KEYS=128
MAX_PAIRS_PER_FRAME=128
FORMAT='MF3D_PASSIVE_SERIALIZER_CAPTURE_V2'

@dataclass(frozen=True)
class SerializerFrame:
    pairs:tuple[tuple[int,int],...]

def decode_serializer_body(body):
    """The same 02 01 tag/value payload used by original offline .mfs import."""
    raw=bytes(body)
    if len(raw)<4 or len(raw)>2+MAX_PAIRS_PER_FRAME*2:
        raise ValueError('Serializer body must contain 1..128 tag/value pairs')
    if raw[:2]!=b'\x02\x01':raise ValueError('Expected serializer header 02 01')
    if (len(raw)-2)%2 or any(v>127 for v in raw):
        raise ValueError('Serializer data must be complete 7-bit tag/value pairs')
    return SerializerFrame(tuple(zip(raw[2::2],raw[3::2])))


def decode_mfs_serializer(raw:bytes)->SerializerFrame:
    """On-disk MidiSerializer::dump() is raw tag/value pairs, NO 02 01 prefix.
    Original importer prepends 02 01 in memory before calling the SysEx handler.
    """
    if not isinstance(raw,bytes) or len(raw)<2 or len(raw)>MAX_PAIRS_PER_FRAME*2 or len(raw)%2:
        raise ValueError('Expected 1..128 raw MFS tag/value pairs')
    if any(b>127 for b in raw):raise ValueError('MFS serializer contains non-7-bit data')
    return SerializerFrame(tuple(zip(raw[::2],raw[1::2])))

def encode_mfs_serializer(pairs)->bytes:
    """Only for offline file transformations, NEVER send to hardware."""
    output=bytearray()
    for key,value in pairs:
        if type(key) is not int or type(value) is not int or not 0<=key<=127 or not 0<=value<=127:
            raise ValueError('Invalid serializer tag/value')
        output.extend((key,value))
        if len(output)>MAX_PAIRS_PER_FRAME*2:raise ValueError('Too many serializer pairs')
    if not output:raise ValueError('Empty serializer')
    return bytes(output)

def decode_serializer_reply(message):
    pkt=parse_sysex(message)
    if not pkt.valid_vendor or pkt.category!='serial-response':return None
    return decode_serializer_body(pkt.family_payload)

@dataclass
class PassiveSerializerCapture:
    frames:list[SerializerFrame]=field(default_factory=list)
    values:dict[int,int]=field(default_factory=dict) # ONLY latest frame
    history_values:dict[int,int]=field(default_factory=dict) # diagnostic, NOT device state
    conflicts:dict[int,list[int]]=field(default_factory=dict)
    def feed(self,message):
        frame=decode_serializer_reply(message)
        if frame is None:return False
        if len(self.frames)>=MAX_FRAMES:raise ValueError('Too many serializer frames')
        latest={};history=dict(self.history_values)
        conflicts={k:list(v) for k,v in self.conflicts.items()}
        for tag,value in frame.pairs:
            if tag in history and history[tag]!=value:
                seen=conflicts.setdefault(tag,[history[tag]])
                if value not in seen:seen.append(value)
            history[tag]=value;latest[tag]=value
        if len(latest)>MAX_KEYS or len(history)>MAX_KEYS:
            raise ValueError('Too many serializer keys')
        self.frames.append(frame)
        self.values=latest
        self.history_values=history
        self.conflicts=conflicts
        return True
    def export(self):
        def entries(values):
            return [dict(tag=t,value=values[t],
                         known_fields=[s.key for s in BY_KEY.values() if s.tag==t],
                         conflict=t in self.conflicts) for t in sorted(values)]
        return dict(format=FORMAT,status='latest_response_only_completion_unverified',
            device='MIDI Fighter 3D (not identity-verified)',read_only=True,
            frames=len(self.frames),observed_tags=entries(self.values),
            history_tags_diagnostics_only=entries(self.history_values),
            conflicts={str(k):list(v) for k,v in sorted(self.conflicts.items())},
            limitations=[
                'Each on-wire reply replaces the previous serializer state in the original Utility.',
                'No verified complete-configuration marker; this is NOT a full device profile.',
                'Unknown settings and identity remain unverified. No device write/flash support.'
            ])
    def save_json(self,path):
        Path(path).write_text(json.dumps(self.export(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
