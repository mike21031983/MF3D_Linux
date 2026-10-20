"""Lossless offline MIDI Fighter .mfs <-> JSON backup.

Original binary data, record order and unknown fields are preserved. This
module cannot contact hardware and never overwrites an existing output file.
"""
import base64,binascii,hashlib,json
from pathlib import Path
from .mfs_container import MfsContainer,Record,MAX_FILE_SIZE
from .serializer_capture import decode_mfs_serializer
FORMAT='MF3D_MFS_LOSSLESS_BACKUP_V1'
MAX_RECORDS=4096

def _encode(value):
    return base64.b64encode(value).decode('ascii')

def _decode(value,limit):
    if not isinstance(value,str) or len(value)>4*((limit+2)//3)+4:
        raise ValueError('Invalid base64 field size')
    try:
        result=base64.b64decode(value,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise ValueError('Invalid base64 data') from exc
    if len(result)>limit:raise ValueError('Field too large')
    return result

def to_document(container):
    raw=container.to_bytes()
    try:
        pairs=decode_mfs_serializer(container.serializer).pairs
        preview=[dict(tag=k,value=v) for k,v in pairs]
    except ValueError:preview=None
    return dict(format=FORMAT,
        note='Offline lossless backup; device compatibility not verified',
        original_sha256=hashlib.sha256(raw).hexdigest(),
        serializer_b64=_encode(container.serializer),
        serializer_preview_only=preview,
        records=[dict(tag=r.tag,kind=r.kind,payload_b64=_encode(r.payload)) for r in container.records])

def from_document(doc):
    if not isinstance(doc,dict) or doc.get('format')!=FORMAT:
        raise ValueError('Unsupported backup format')
    records=doc.get('records')
    if not isinstance(records,list) or len(records)>MAX_RECORDS:
        raise ValueError('Invalid record count')
    serializer=_decode(doc.get('serializer_b64'),65535)
    result=[]
    for item in records:
        if not isinstance(item,dict):raise ValueError('Invalid record')
        tag=item.get('tag');kind=item.get('kind')
        if type(tag) is not int or not 0<=tag<=65535:raise ValueError('Invalid tag')
        if type(kind) is not int or not 0<=kind<=255:raise ValueError('Invalid kind')
        result.append(Record(tag,kind,_decode(item.get('payload_b64'),65535)))
    container=MfsContainer(serializer,tuple(result))
    binary=container.to_bytes()
    digest=doc.get('original_sha256')
    if not isinstance(digest,str) or len(digest)!=64 or hashlib.sha256(binary).hexdigest()!=digest:
        raise ValueError('SHA256 mismatch: refusing to restore modified data')
    return container

def backup(source,output):
    obj=to_document(MfsContainer.from_path(source))
    with Path(output).open('x',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write('\n')

def restore(source,output):
    src=Path(source)
    if src.stat().st_size>4*MAX_FILE_SIZE:raise ValueError('Backup too large')
    data=from_document(json.loads(src.read_text(encoding='utf-8'))).to_bytes()
    with Path(output).open('xb') as f:f.write(data)
