"""Documented USB-MIDI interface for Midi Fighter 3D.
Source: DJ TechTools User Guide v1.03, pp. 2,4–8,14–19.
Channel numbers here follow the guide: 0..15.
Persistent configuration/flash/DFU SysEx deliberately NOT supported.
"""
from dataclasses import dataclass
from enum import IntEnum
CHANNEL_NOTES=3
CHANNEL_AUX=4

@dataclass(frozen=True)
class MidiCommand:
    kind:str
    channel:int
    note:int
    velocity:int
    def __post_init__(self):
        if self.kind not in ('note_on','note_off'):
            raise ValueError('Invalid event')
        if not 0<=self.channel<=15 or not 0<=self.note<=127 or not 0<=self.velocity<=127:
            raise ValueError('Invalid MIDI value')
    def to_mido(self):
        import mido
        return mido.Message(self.kind,channel=self.channel,note=self.note,velocity=self.velocity)

def note_for_pad(bank:int,pad:int)->int:
    if bank not in range(4) or pad not in range(16):
        raise ValueError('Invalid bank or pad')
    row,col=divmod(pad,4)
    return 36+bank*16+(3-row)*4+col

def pad_for_note(bank:int,note:int):
    if bank not in range(4):raise ValueError('Invalid bank')
    base=36+bank*16
    if not base<=note<=base+15:return None
    index=note-base
    return (3-index//4)*4+index%4

def color(bank:int,pad:int,velocity:int,channel:int=CHANNEL_NOTES)->MidiCommand:
    return MidiCommand('note_on',channel,note_for_pad(bank,pad),velocity)

def animation(bank:int,pad:int,velocity:int,channel:int=CHANNEL_AUX)->MidiCommand:
    return MidiCommand('note_on',channel,note_for_pad(bank,pad),velocity)

def switch_bank(bank:int,channel:int=CHANNEL_AUX)->MidiCommand:
    if bank not in range(4):raise ValueError('Invalid bank')
    return MidiCommand('note_on',channel,bank,127)

def describe_incoming(message,bank:int=0,notes_channel:int=CHANNEL_NOTES,aux_channel:int=CHANNEL_AUX)->str:
    typ=getattr(message,'type',None)
    if typ in ('note_on','note_off'):
        ch=getattr(message,'channel',-1)
        note=getattr(message,'note',-1)
        vel=getattr(message,'velocity',0)
        if ch==notes_channel:
            pad=pad_for_note(bank,note)
            if pad is not None:
                return f'Пэд {pad+1}: {"нажат" if typ=="note_on" and vel else "отпущен"}, velocity={vel}'
        if ch==aux_channel and note in range(4):
            return f'Банк {note+1}: {"выбран" if typ=="note_on" and vel else "выключен"}'
        return f'Нота {note} ch{ch}, velocity={vel}, {typ}'
    if typ=='control_change':
        ch=getattr(message,'channel',-1)
        cc=getattr(message,'control',-1)
        val=getattr(message,'value',-1)
        return f'CC{cc} ch{ch}={val}'+(' [наклон]' if ch==aux_channel and 0<=cc<=7 else '')
    if typ=='sysex':return 'SysEx получен (только отображение)'
    return str(message)
