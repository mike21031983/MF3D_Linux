"""Passive 02 01 settings responses, not full config completion.

Mac ConfigWidget::sysEx (0x100104820) reads tag/value pairs from
body[2:] and passes them to MidiSerializer::write. No device writes here.
No completion marker for serializer data has been independently proven.
"""
from dataclasses import dataclass,field
import json
from pathlib import Path
from .vendor_sysex import parse_sysex
from .device_profile import BY_KEY
FORMAT='MF3D_PASSIVE_SERIALIZER_CAPTURE_V1'
MAX_FRAMES=64
MAX_PAIRS_PER_FRAME=128

@dataclass(frozen=True)
class SerializerFrame:
    pairs:tuple[tuple[int,int],...]

def decode_serializer_reply(message):
    packet=parse_sysex(message)
    if not packet.valid_vendor or packet.category!='serial-response':
        return None
    data=packet.family_payload[2:]
    if len(data)<2 or len(data)%2 or len(data)>MAX_PAIRS_PER_FRAME*2:
        raise ValueError('Serializer reply must contain 1..128 tag/value pairs')
    return SerializerFrame(tuple(zip(data[::2],data[1::2])))

@dataclass
class PassiveSerializerCapture:
    frames:list[SerializerFrame]=field(default_factory=list)
    values:dict[int,int]=field(default_factory=dict)
    conflicts:dict[int,list[int]]=field(default_factory=dict)
    def feed(self,message):
        frame=decode_serializer_reply(message)
        if frame is None:return False
        if len(self.frames)>=MAX_FRAMES:raise ValueError('Too many serializer frames')
        proposed=dict(self.values)
        conflicts={k:list(v) for k,v in self.conflicts.items()}
        for tag,value in frame.pairs:
            if tag in proposed and proposed[tag]!=value:
                history=conflicts.setdefault(tag,[proposed[tag]])
                if value not in history:history.append(value)
            proposed[tag]=value
        if len(proposed)>128:raise ValueError('Too many settings')
        self.values=proposed
        self.conflicts=conflicts
        self.frames.append(frame)
        return True
    def export(self):
        entries=[]
        for tag in sorted(self.values):
            fields=[s.key for s in BY_KEY.values() if s.tag==tag]
            entries.append(dict(tag=tag,value=self.values[tag],
                                known_fields=fields,conflict=tag in self.conflicts))
        return dict(format=FORMAT,
            status='partial_observation_not_verified_full_config',
            device='MIDI Fighter 3D (not identity-verified)',
            read_only=True,frames=len(self.frames),observed_tags=entries,
            conflicts={str(k):list(v) for k,v in sorted(self.conflicts.items())},
            limitations=['Device family/model not verified by this packet',
                'No verified full-config completion signal',
                'Do not write observed values to EEPROM or firmware'])
    def save_json(self,path):
        Path(path).write_text(json.dumps(self.export(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
