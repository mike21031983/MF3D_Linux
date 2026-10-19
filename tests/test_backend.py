import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from mf3d_linux.midi_backend import MidiBackend
from mf3d_linux.protocol import color

class FakePort:
    def __init__(self):self.sent=[];self.closed=False
    def send(self,msg):self.sent.append(msg)
    def iter_pending(self):return iter([SimpleNamespace(type='note_on',channel=3,note=48,velocity=127)])
    def close(self):self.closed=True

class TestBackend(unittest.TestCase):
    def test_no_hardware_no_send(self):
        backend=MidiBackend()
        self.assertIsNone(backend.input)
        self.assertIsNone(backend.output)
        with self.assertRaises(RuntimeError):backend.send(color(0,0,13))
    def test_mock_alsa_ports(self):
        received=FakePort()
        transmitted=FakePort()
        mido=SimpleNamespace(
            get_input_names=lambda:['Midi Fighter 3D'],
            get_output_names=lambda:['Midi Fighter 3D'],
            open_input=lambda name:received,
            open_output=lambda name:transmitted,
        )
        mido.Message=lambda typ,**kw:SimpleNamespace(type=typ,**kw)
        with patch.dict(sys.modules,{'mido':mido,'rtmidi':SimpleNamespace()}):
            backend=MidiBackend()
            backend.connect()
            self.assertEqual(len(backend.poll()),1)
            backend.send(color(0,0,13))
            self.assertEqual(transmitted.sent[0].note,48)
            self.assertEqual(transmitted.sent[0].velocity,13)
            backend.disconnect()
            self.assertTrue(received.closed)
            self.assertTrue(transmitted.closed)

if __name__=='__main__':unittest.main()
