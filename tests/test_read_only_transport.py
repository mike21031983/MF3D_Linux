"""All tests are offline: never send a message to physical devices."""
import unittest
from types import SimpleNamespace
from mf3d_linux.midi_backend import MidiBackend
class FakeOutput:
    def __init__(self):self.sent=[]
    def send(self,msg):self.sent.append(msg)
class ReadOnlyTransportTests(unittest.TestCase):
    def test_only_read_request(self):
        port=FakeOutput();backend=MidiBackend()
        backend.output=port;backend.output_name='MIDI Fighter 3D'
        backend.mido=SimpleNamespace(Message=lambda kind,**kw:(kind,kw))
        backend.send_color_read_request(1)
        self.assertEqual(port.sent,[('sysex',{'data':b'\x00\x01\x79\x04\x01\x01'})])
        with self.assertRaises(ValueError):backend.send_color_read_request(3)
        self.assertEqual(len(port.sent),1)
    def test_reject_other_midi_ports(self):
        backend=MidiBackend();backend.output=FakeOutput()
        backend.output_name='Generic USB-MIDI OUT'
        backend.mido=SimpleNamespace(Message=lambda *a,**kw:None)
        with self.assertRaises(RuntimeError):backend.send_color_read_request(1)
        self.assertEqual(backend.output.sent,[])
    def test_disconnected_no_send(self):
        backend=MidiBackend()
        with self.assertRaises(RuntimeError):backend.send_color_read_request(1)
if __name__=='__main__':unittest.main()
