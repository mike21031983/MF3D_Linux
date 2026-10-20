"""Native Linux ALSA/RtMidi MIDI backend via mido/python-rtmidi."""
class MidiBackend:
    def __init__(self):
        self.input=None
        self.output=None
        self.input_name=None
        self.output_name=None
        self.mido=None
        self.verified_identity=None
        self.identity_pending=False
    def available(self):
        try:
            import mido
            import rtmidi
        except ImportError as e:
            return [],[],f'Установите python3-mido и python3-rtmidi: {e}'
        self.mido=mido
        try:return mido.get_input_names(),mido.get_output_names(),None
        except Exception as e:return [],[],str(e)
    def connect(self,input_name=None,output_name=None):
        ins,outs,err=self.available()
        if err:raise RuntimeError(err)
        if input_name is None:input_name=next((x for x in ins if 'midi fighter' in x.lower()),None)
        if output_name is None:output_name=next((x for x in outs if 'midi fighter' in x.lower()),None)
        if input_name not in ins or output_name not in outs:
            raise RuntimeError('Не найдены оба MIDI порта для подключения')
        new_in=self.mido.open_input(input_name)
        try:new_out=self.mido.open_output(output_name)
        except Exception:
            new_in.close()
            raise
        self.disconnect()
        self.input,self.output=new_in,new_out
        self.input_name,self.output_name=input_name,output_name
    def disconnect(self):
        for port in (self.input,self.output):
            if port:
                try:port.close()
                except Exception:pass
        self.input=self.output=None
        self.input_name=self.output_name=None
        self.verified_identity=None
        self.identity_pending=False
    def poll(self,limit=128):
        if not self.input:return []
        return list(self.input.iter_pending())[:limit]
    def send(self,command):
        if not self.output:raise RuntimeError('Контроллер MIDI не подключён')
        self.output.send(command.to_mido())

    def _check_mf3d_port(self):
        if self.output is None or self.input is None or self.mido is None:
            raise RuntimeError('USB-MIDI input and output must both be connected')
        if not self.output_name or not self.input_name or (
            'midi fighter' not in self.output_name.casefold() or
            'midi fighter' not in self.input_name.casefold()):
            raise RuntimeError('Expected MIDI Fighter input AND output ports')

    def request_identity(self):
        """Explicit vendor identity READ, not firmware or configuration write."""
        from .device_identity import identity_request
        self._check_mf3d_port()
        self.verified_identity=None
        self.identity_pending=False
        self.output.send(self.mido.Message('sysex',data=identity_request()[1:-1]))
        self.identity_pending=True

    def observe_identity(self,message):
        from .device_identity import decode_identity_reply
        if not self.identity_pending:return None
        identity=decode_identity_reply(message)
        if identity is not None:
            self.identity_pending=False
            self.verified_identity=identity if identity.is_standard_mf3d else None
        return identity

    def expire_identity(self):
        self.identity_pending=False
        self.verified_identity=None

    def _require_verified_mf3d(self):
        self._check_mf3d_port()
        if self.identity_pending or self.verified_identity is None or not self.verified_identity.is_standard_mf3d:
            raise RuntimeError('Model not verified as MF3D 0003:0001')

    def send_color_read_request(self,tag):
        """Explicit vendor BULK READ only; no EEPROM/DFU/reset/write."""
        from .bulk_read import build_bulk_read_request
        self._require_verified_mf3d()
        frame=build_bulk_read_request(tag)
        self.output.send(self.mido.Message('sysex',data=frame[1:-1]))

    def send_main_config_read_request(self):
        """Explicit vendor main-config READ only. No settings writes or flashing."""
        from .config_read import build_main_config_read_request
        self._require_verified_mf3d()
        frame=build_main_config_read_request()
        self.output.send(self.mido.Message('sysex',data=frame[1:-1]))
