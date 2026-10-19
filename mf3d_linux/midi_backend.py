"""Native Linux ALSA/RtMidi MIDI backend via mido/python-rtmidi."""
class MidiBackend:
    def __init__(self):
        self.input=None
        self.output=None
        self.input_name=None
        self.output_name=None
        self.mido=None
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
    def poll(self,limit=128):
        if not self.input:return []
        return list(self.input.iter_pending())[:limit]
    def send(self,command):
        if not self.output:raise RuntimeError('Контроллер MIDI не подключён')
        self.output.send(command.to_mido())
