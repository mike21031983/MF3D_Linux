"""Single user-triggered MF3D READ diagnostic session. NO device I/O.

Requires caller to dispatch the four allowlisted requests; consumes replies.
The main configuration never claims a verified completion marker. Raw SysEx
can include a private identifier: traces are saved only on explicit request.
"""
from __future__ import annotations
import json
from pathlib import Path
from .device_identity import identity_request,decode_identity_reply
from .config_read import build_main_config_read_request
from .bulk_read import build_bulk_read_request
from .color_read_session import ColorReadSession
from .serializer_capture import PassiveSerializerCapture
from .vendor_sysex import parse_sysex

READS={identity_request(),build_main_config_read_request(),
       build_bulk_read_request(1),build_bulk_read_request(2)}
MAX_TRACE_EVENTS=256

class AuditSession:
    """One-shot, no retries; caller transmits returned READ frames explicitly."""
    def __init__(self,identity_timeout=3.0,settings_timeout=4.0,color_timeout=4.0):
        self.identity_timeout=identity_timeout
        self.settings_timeout=settings_timeout
        self.color_timeout=color_timeout
        self.phase='idle';self.deadline=None;self.identity=None
        self.config=PassiveSerializerCapture()
        self.colors=ColorReadSession(timeout_seconds=color_timeout)
        self.warning=[];self.trace=[];self.error=None

    @property
    def running(self):
        return self.phase in ('identity','settings','colors')

    def _record(self,direction,frame):
        if len(self.trace)<MAX_TRACE_EVENTS:
            self.trace.append({'direction':direction,'sysex':frame.hex(' ').upper()})
        elif len(self.trace)==MAX_TRACE_EVENTS:
            self.warning.append('Trace reached 256 event limit; additional frames omitted')
            self.trace.append({'direction':'limit','sysex':''})

    def _tx(self,frame):
        if frame not in READS:raise ValueError('Disallowed vendor SysEx frame')
        self._record('tx',frame)
        return frame

    def begin(self,now):
        if self.phase!='idle':raise RuntimeError('Session already started')
        self.phase='identity';self.deadline=now+self.identity_timeout
        return self._tx(identity_request())

    def feed(self,frame,now):
        """Consume SysEx; return the next read query, or None."""
        if not self.running:return None
        if self.deadline is not None and now>=self.deadline:
            self.tick(now);return None
        if isinstance(frame,bytes) and (len(frame)<5 or frame[0]!=0xF0 or frame[-1]!=0xF7):
            raise ValueError('Expected complete F0..F7 frame')
        parsed=parse_sysex(frame)
        if not parsed.valid_vendor:return None
        self._record('rx',frame if isinstance(frame,bytes) else
                     bytes((0xF0,*frame.data,0xF7)))
        if self.phase=='identity':
            try:identity=decode_identity_reply(frame)
            except ValueError as exc:
                self.fail('Invalid identity response: '+str(exc));return None
            if identity is None:return None
            if not identity.is_standard_mf3d:
                self.fail('Different MIDI Fighter model: configuration reads blocked')
                return None
            self.identity=identity
            self.phase='settings';self.deadline=now+self.settings_timeout
            return self._tx(build_main_config_read_request())
        if self.phase=='settings':
            try:matched=self.config.feed(frame)
            except ValueError as exc:
                self.warning.append('Bad main settings response: '+str(exc))
                return None
            if not matched:return None
            return self._begin_colors(now)  # NOT proof of full settings completion
        if self.phase=='colors':
            try:query=self.colors.feed(frame,now)
            except (ValueError,TimeoutError,RuntimeError) as exc:
                self.fail('Invalid color transfer: '+str(exc));return None
            if query is not None:return self._tx(query)
            if self.colors.state=='complete':
                self.phase='finished';self.deadline=None
        return None

    def _begin_colors(self,now):
        self.phase='colors';self.deadline=None
        self.colors=ColorReadSession(timeout_seconds=self.color_timeout)
        return self._tx(self.colors.begin(now))

    def tick(self,now):
        """Nonblocking timeout check, optionally yielding a color read request."""
        if self.phase=='identity' and now>=self.deadline:
            self.fail('Identity request timed out; device not verified')
        elif self.phase=='settings' and now>=self.deadline:
            self.warning.append('Settings 02 01 did not arrive; continuing LED reads')
            return self._begin_colors(now)
        elif self.phase=='colors' and self.colors.expire(now):
            self.fail('Color block timeout; partial LED data discarded')
        return None

    def fail(self,reason):
        self.phase='failed';self.error=reason;self.deadline=None
        if self.colors.state=='reading':self.colors.fail(reason)

    def report(self):
        if self.running:raise RuntimeError('Still reading; report not final')
        if self.phase=='idle':raise RuntimeError('No diagnostic session started')
        colors=self.colors.snapshot() if self.colors.state=='complete' else None
        return {'format':'MF3D_CP10_READ_AUDIT_V1',
            'status':'colors_complete_settings_unverified' if colors is not None else 'incomplete',
            'read_only':True,
            'identity':({'family':self.identity.family_code,'model':self.identity.model_number}
                        if self.identity is not None else None),
            'main_settings':self.config.export() if self.config.frames else None,
            'main_settings_complete':False,
            'led_colors_complete':colors is not None,
            'inactive_rgb7':list(colors[1]) if colors is not None else None,
            'active_rgb7':list(colors[2]) if colors is not None else None,
            'error':self.error,'warnings':list(self.warning),
            'note':'Identity provisional; NO persistent device writes. NOT a verified full hardware profile.'}

    def trace_document(self):
        if self.phase=='idle':raise RuntimeError('No trace')
        return {'format':'MF3D_OFFLINE_TRACE_V1',
                'privacy_warning':'RAW SysEx may expose device identity. Keep private.',
                'events':[event for event in self.trace if event['direction'] in ('tx','rx')]}

    def save_report(self,path):
        with Path(path).open('x',encoding='utf-8') as f:
            json.dump(self.report(),f,indent=2,ensure_ascii=False);f.write('\n')

    def save_trace(self,path):
        with Path(path).open('x',encoding='utf-8') as f:
            json.dump(self.trace_document(),f,indent=2,ensure_ascii=False);f.write('\n')
