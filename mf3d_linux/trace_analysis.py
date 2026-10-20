"""Offline-only MF3D MIDI transcript interpreter for later one-shot hardware validation.

Never opens MIDI ports; reconstructs the identity/settings/color read workflow
using conservative decoders. Input is an explicit JSON array of MIDI SysEx.
Raw identity frames might contain device-specific identifiers; keep them private.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from .device_identity import identity_request,decode_identity_reply
from .config_read import build_main_config_read_request
from .bulk_read import build_bulk_read_request,ColorBulkCapture
from .serializer_capture import PassiveSerializerCapture
from .vendor_sysex import parse_sysex

FORMAT='MF3D_OFFLINE_TRACE_V1'
MAX_EVENTS=512
MAX_TRACE_BYTES=1048576

def decode_hex(text):
    if not isinstance(text,str) or len(text)>16384*3:
        raise ValueError('Invalid or oversized SysEx hex')
    try: data=bytes.fromhex(text)
    except ValueError as exc: raise ValueError('Invalid hex bytes') from exc
    if len(data)<5 or len(data)>8192 or data[0]!=0xF0 or data[-1]!=0xF7:
        raise ValueError('Expected complete F0 ... F7 SysEx frame')
    parse_sysex(data)
    return data

def inspect(events):
    if not isinstance(events,list) or len(events)>MAX_EVENTS:
        raise ValueError('Expected <=512 trace events')
    identity=None;identity_pending=False
    config_pending=False;config=PassiveSerializerCapture()
    colors={};warnings=[];stats={'tx':0,'rx':0,'ignored':0,'errors':0}
    for i,event in enumerate(events):
        if not isinstance(event,dict) or event.get('direction') not in ('tx','rx'):
            raise ValueError(f'Event {i}: expected tx/rx direction')
        direction=event['direction'];packet=decode_hex(event.get('sysex'))
        stats[direction]+=1
        if direction=='tx':
            if packet==identity_request():
                identity_pending=True;identity=None
                config_pending=False;config=PassiveSerializerCapture();colors={}
            elif packet==build_main_config_read_request():
                if identity is None or not identity.is_standard_mf3d:
                    warnings.append(f'Event {i}: settings requested without verified MF3D identity')
                config_pending=bool(identity and identity.is_standard_mf3d)
                config=PassiveSerializerCapture()
            elif packet in (build_bulk_read_request(1),build_bulk_read_request(2)):
                tag=packet[-2]
                if identity is None or not identity.is_standard_mf3d:
                    warnings.append(f'Event {i}: color block {tag} requested without verified model')
                else:
                    colors[tag]=ColorBulkCapture(tag)
            else:
                warnings.append(f'Event {i}: unrecognized outgoing SysEx; not assumed safe')
            continue
        if identity_pending:
            try:found=decode_identity_reply(packet)
            except ValueError as exc:
                warnings.append(f'Event {i}: malformed identity response: {exc}')
                stats['errors']+=1;identity_pending=False
                continue
            if found is not None:
                identity_pending=False;identity=found
                if not found.is_standard_mf3d:
                    warnings.append(f'Event {i}: response identifies a different model')
                continue
        parsed=parse_sysex(packet)
        if config_pending and parsed.category=='serial-response':
            try:config.feed(packet)
            except ValueError as exc:
                stats['errors']+=1
                warnings.append(f'Event {i}: invalid settings frame: {exc}')
            continue
        if parsed.category=='bulk-response' and len(parsed.family_payload)>=3:
            tag=parsed.family_payload[2]
            capture=colors.get(tag)
            if capture is not None and not capture.complete and not capture.error:
                try:capture.feed(packet)
                except ValueError as exc:
                    stats['errors']+=1
                    warnings.append(f'Event {i}: invalid color block {tag}: {exc}')
                continue
        stats['ignored']+=1
    identity_summary=(dict(family=identity.family_code,model=identity.model_number,
                           standard_mf3d=identity.is_standard_mf3d)
                      if identity is not None else None)
    color_status={}
    for tag in (1,2):
        capture=colors.get(tag)
        data=(bytes(capture.get_values()) if capture and capture.complete else None)
        color_status[str(tag)]={
            'requested':capture is not None,
            'complete':bool(capture and capture.complete),
            'received_values':len(capture.received) if capture else 0,
            'packet_count':len(capture.packets) if capture else 0,
            'sha256_if_complete':hashlib.sha256(data).hexdigest() if data else None,
            'error':capture.error if capture else None,
        }
    return {
        'format':'MF3D_OFFLINE_TRACE_REPORT_V1','read_only_analysis':True,
        'note':'Static/provisional identity field decoding; not live hardware validation',
        'events_analyzed':len(events),'statistics':stats,'identity':identity_summary,
        'settings':{
            'requested':config_pending,'reply_frames':len(config.frames),
            'latest_pairs':len(config.values),'latest_tags':sorted(config.values),
            'status':'latest_response_only_completion_unverified',
        },
        'colors':color_status,'warnings':warnings,
        'limitations':['A successful identity parse is not cryptographic authentication.',
                       'Main settings never considered complete without further proof.',
                       'A missing trace event may reflect capture loss, not firmware failure.'],
    }

def inspect_file(path):
    p=Path(path)
    if p.stat().st_size>MAX_TRACE_BYTES:raise ValueError('Trace exceeds 1 MiB')
    doc=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(doc,dict) or doc.get('format')!=FORMAT:
        raise ValueError('Not a supported MF3D transcript')
    return inspect(doc.get('events'))
