import unittest
from types import SimpleNamespace
from mf3d_linux.config_read import build_main_config_read_request
from mf3d_linux.midi_backend import MidiBackend
class Port:
    def __init__(self):self.sent=[]
    def send(self,msg):self.sent.append(msg)
class TestRequest(unittest.TestCase):
    def test_exact_wire_bytes(self):
        self.assertEqual(build_main_config_read_request().hex(' '),'f0 00 01 79 02 00 f7')
    def test_guarded_port(self):
        b=MidiBackend();b.output=Port();b.output_name='Other'
        b.mido=SimpleNamespace(Message=lambda *a,**kw:None)
        with self.assertRaises(RuntimeError):b.send_main_config_read_request()
        self.assertEqual(b.output.sent,[])
    def test_valid_named_port(self):
        b=MidiBackend();b.output=Port();b.output_name='MIDI Fighter 3D'
        b.mido=SimpleNamespace(Message=lambda typ,**kw:(typ,kw))
        b.send_main_config_read_request()
        self.assertEqual(b.output.sent,[('sysex',{'data':b'\x00\x01\x79\x02\x00'})])
if __name__=='__main__':unittest.main()
