"""Offline .mfs container inspector. Based on disassembled ConfigWidget::buildMfsBlob/importSettingsFromBlob from bundled macOS Utility.
Format: uint16 BE serializer_length, serializer bytes, then repeat uint16 BE tag, uint8 type, uint16 BE data_length, data.
NO MIDI messages or firmware operations. Compatibility with actual exported .mfs awaits a real sample.
"""
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE=1_048_576
@dataclass(frozen=True)
class Record:
    tag:int
    kind:int
    payload:bytes
    def __post_init__(self):
        if not 0<=self.tag<=65535 or not 0<=self.kind<=255 or len(self.payload)>65535:
            raise ValueError('Invalid MFS record')

@dataclass(frozen=True)
class MfsContainer:
    serializer:bytes
    records:tuple[Record,...]
    @classmethod
    def parse(cls,data:bytes):
        if not isinstance(data,bytes) or not 2<=len(data)<=MAX_FILE_SIZE:
            raise ValueError('Invalid MFS length')
        n=int.from_bytes(data[:2],'big')
        if n>len(data)-2:raise ValueError('Truncated MFS serializer')
        serializer=data[2:2+n];i=2+n;records=[]
        while i<len(data):
            if len(data)-i<5:raise ValueError('Truncated MFS record header')
            tag=int.from_bytes(data[i:i+2],'big')
            kind=data[i+2]
            length=int.from_bytes(data[i+3:i+5],'big')
            i+=5
            if length>len(data)-i:raise ValueError('Truncated MFS record payload')
            records.append(Record(tag,kind,data[i:i+length]))
            if len(records)>4096:raise ValueError('Too many MFS records')
            i+=length
        return cls(serializer,tuple(records))
    @classmethod
    def from_path(cls,path):
        p=Path(path)
        if p.stat().st_size>MAX_FILE_SIZE:raise ValueError('MFS file exceeds safety bound')
        return cls.parse(p.read_bytes())
    def to_bytes(self):
        if len(self.serializer)>65535:raise ValueError('Serializer too large')
        out=bytearray(len(self.serializer).to_bytes(2,'big'))
        out.extend(self.serializer)
        for r in self.records:
            out.extend(r.tag.to_bytes(2,'big'))
            out.append(r.kind)
            out.extend(len(r.payload).to_bytes(2,'big'))
            out.extend(r.payload)
        if len(out)>MAX_FILE_SIZE:raise ValueError('MFS output too large')
        return bytes(out)
    def describe(self):
        lines=['Файл .mfs — автономный анализ без записи в устройство',
            f'Основные данные (serializer): {len(self.serializer)} байт',
            f'Дополнительных записей: {len(self.records)}']
        for n,r in enumerate(self.records,1):
            title=('Цвета отпущенных кнопок' if (r.tag,r.kind)==(1,1) else
                'Цвета нажатых кнопок' if (r.tag,r.kind)==(2,1) else
                'Неизвестный/общий блок')
            lines.append(f'Блок {n}: tag={r.tag}, type={r.kind}, length={len(r.payload)} — {title}')
        # Original offline importer feeds serializer bytes to ConfigWidget::sysEx
        # with import flag set. Decode 02 01 directly, without synthesizing a SysEx.
        try:
            from .serializer_capture import decode_serializer_body
            from .device_profile import BY_KEY
            decoded=decode_serializer_body(self.serializer)
        except (ValueError,TypeError):
            lines.append('Сериализатор: заголовок 02 01 не распознан или пары повреждены; байты сохранены')
        else:
            lines.append('Основные параметры 02 01: '+str(len(decoded.pairs))+
                         ' пар (полнота не подтверждена)')
            for tag,value in decoded.pairs:
                names=', '.join(s.key for s in BY_KEY.values() if s.tag==tag)
                lines.append(f'  tag {tag}: значение {value}'+
                             (f' — {names}' if names else ' — неизвестный параметр'))
        for record in self.records:
            if record.tag in (1,2) and record.kind==1:
                lines.append(f'RGB7 block {record.tag}: '+(
                    '192 байта (ожидаемый размер)' if len(record.payload)==192
                    else f'НЕОЖИДАННЫЙ размер {len(record.payload)} (ожидалось 192)'))
        lines.append('Внимание: синтетические проверки пройдены, но реальный .mfs ещё не предоставлен.')
        return '\n'.join(lines)
