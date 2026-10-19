"""MIDI Fighter 3D model 0001 settings + 4 x 16 RGB color banks.

Independently written from field declarations in bundled vendor
device.mf_3d.js. Offline-only: NO hardware writes or firmware operations.
"""
import json
from pathlib import Path
from dataclasses import dataclass,field

FORMAT='MF3D_LINUX_PROFILE_V1'
PALETTE=('#FF0000','#FF4500','#FFBF00','#BFFF00','#00FF00',
         '#00FFFF','#0000FF','#DD04EE','#FF005F','#FFFFFF',
         '#4F0000','#5F2000','#4F2F00','#5F7F00','#002F00',
         '#003F3F','#00003F','#2F042F','#5F002F','#000000')
@dataclass(frozen=True)
class Setting:
    key:str
    page:str
    tag:int
    kind:str
    default:int
    minimum:int=0
    maximum:int=127
    options:tuple=()
    bit_offset:int=0
    bit_width:int=7
    label:str=''

SETTINGS=(
    Setting('midi_channel','settings',0,'int',3,1,16,label='MIDI Channel (GUI 1..16)'),
    Setting('midi_velocity','settings',1,'percent',127,label='MIDI Velocity'),
    Setting('software_mode','settings',7,'enum',0,options=('Traktor','Ableton'),label='Software Mode'),
    Setting('combos','settings',8,'bool',1,label='Combos'),
    Setting('sleep_timer','settings',22,'int',60,0,120,label='Sleep Timer'),
    Setting('bank_buttons','settings',3,'enum',0,options=('Four Banks Enabled','Disabled Hold','Disabled Toggle'),label='Bank Buttons'),
    Setting('bank_side_buttons','settings',23,'bool',1,label='Bank Side Buttons'),
    Setting('motion_animation','settings',10,'bitflag',3,0,3,options=('Button Pitch','Edge Tilt'),bit_offset=1,bit_width=2,label='Motion animation'),
    Setting('button_animation','settings',10,'enum',3,0,5,options=('Square','Circle','Star','Triangle','Spark','None'),bit_offset=3,bit_width=3,label='Button animation'),
    Setting('rotation','motion',11,'enum',1,options=('Disabled','Relative','Absolute','ENC 3FH/41H'),label='Rotation'),
    Setting('pickup_sensitivity','motion',21,'percent',127,label='Pickup Sensitivity'),
    Setting('rotation_range','motion',17,'int',60,15,90,label='Rotation Range (deg)'),
    Setting('tilt_directions','motion',12,'bitflag',15,0,15,options=('Left','Front','Right','Back'),bit_width=4,label='Tilt Directions'),
    Setting('join_tilt','motion',20,'bitflag',0,0,3,options=('On X','On Y'),bit_width=2,label='Join Tilt CCs'),
    Setting('tilt_dead_zone','motion',18,'int',12,1,30,label='Tilt Dead Zone'),
    Setting('tilt_range','motion',16,'int',70,15,85,label='Tilt Range'),
    Setting('tilt_sensitivity','motion',14,'percent',127,label='Tilt Sensitivity'),
)
BY_KEY={x.key:x for x in SETTINGS}
def encode_color(rgb):
    if len(rgb)!=7 or rgb[0]!='#' or any(x not in '0123456789abcdefABCDEF' for x in rgb[1:]):
        raise ValueError('Expected #RRGGBB')
    return tuple(int(rgb[i:i+2],16)//2 for i in (1,3,5))
def decode_color(values):
    if len(values)!=3 or any(type(x) is not int or not 0<=x<=127 for x in values):
        raise ValueError('Expected three RGB7 bytes')
    return '#'+''.join(f'{v*2:02X}' for v in values)
@dataclass
class Profile:
    settings:dict=field(default_factory=lambda:{x.key:x.default for x in SETTINGS})
    inactive:list=field(default_factory=lambda:['#000000']*64)
    active:list=field(default_factory=lambda:['#FFFFFF']*64)
    animation_reserved:int=0
    def validate(self):
        if set(self.settings)!=set(BY_KEY):raise ValueError('Settings keys invalid')
        for name,n in self.settings.items():
            s=BY_KEY[name]
            if type(n) is not int or not s.minimum<=n<=s.maximum:raise ValueError(name)
            if s.kind=='enum' and n>=len(s.options):raise ValueError(name)
        if type(self.animation_reserved) is not int or not 0<=self.animation_reserved<=255:
            raise ValueError('Reserved value invalid')
        for label in ('inactive','active'):
            arr=getattr(self,label)
            if not isinstance(arr,list) or len(arr)!=64:raise ValueError(label)
            for rgb in arr:encode_color(rgb)
        return self
    def color_buffer(self,state):
        if state not in ('inactive','active'):raise ValueError(state)
        self.validate()
        return [v for color in getattr(self,state) for v in encode_color(color)]
    def set_color_buffer(self,state,data):
        if state not in ('inactive','active'):raise ValueError(state)
        data=list(data)
        if len(data)!=192:raise ValueError('192 RGB7 values expected')
        setattr(self,state,[decode_color(data[i:i+3]) for i in range(0,192,3)])
        return self
    def tag10(self):
        return ((self.animation_reserved&~0x3E) |
                ((self.settings['motion_animation']&3)<<1) |
                ((self.settings['button_animation']&7)<<3))
    def set_tag10(self,val):
        if type(val) is not int or not 0<=val<=255:raise ValueError('Invalid tag byte')
        motion=(val>>1)&3
        button=(val>>3)&7
        if button>=6:raise ValueError('Unknown animation code')
        self.animation_reserved=val & ~0x3E
        self.settings['motion_animation']=motion
        self.settings['button_animation']=button
    def as_dict(self):
        self.validate()
        return {'format':FORMAT,'device':'MIDI Fighter 3D','family':'0003','model':'0001',
                'settings':dict(self.settings),'reserved_tag_10':self.animation_reserved,
                'colors_inactive':list(self.inactive),'colors_active':list(self.active)}
    def save(self,path):
        Path(path).write_text(json.dumps(self.as_dict(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    @classmethod
    def load(cls,path):
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        if d.get('format')!=FORMAT or d.get('family')!='0003' or d.get('model')!='0001':
            raise ValueError('Not a MF3D 0001 profile')
        return cls(settings=d['settings'],inactive=d['colors_inactive'],active=d['colors_active'],
                   animation_reserved=d.get('reserved_tag_10',0)).validate()
