"""CP08 identity and safe read gate tests: simulation only, no MIDI hardware."""
import unittest
from types import SimpleNamespace
from mf3d_linux.device_identity import identity_request,decode_identity_reply
from mf3d_linux.midi_backend import MidiBackend

def reply(family=3,model=1):
    return bytes((0xF0,0,1,0x79,5,1,11,22,family,0,model,0,1,2,3,4,0xF7))

class Port:
    def __init__(self):self.sent=[];self.closed=False
    def send(self,message):self.sent.append(message)
    def close(self):self.closed=True

class IdentityTests(unittest.TestCase):
    def make_backend(self):
        b=MidiBackend();b.input=Port();b.output=Port()
        b.input_name='MIDI Fighter 3D';b.output_name='MIDI Fighter 3D'
        b.mido=SimpleNamespace(Message=lambda typ,**args:(typ,args))
        return b
    def test_wire_request(self):
        self.assertEqual(identity_request().hex(' '),'f0 00 01 79 05 f7')
    def test_parse_normal_and_other_model(self):
        ident=decode_identity_reply(reply())
        self.assertEqual((ident.family_code,ident.model_number),('0003','0001'))
        self.assertTrue(ident.is_standard_mf3d)
        self.assertFalse(decode_identity_reply(reply(model=2)).is_standard_mf3d)
        self.assertFalse(decode_identity_reply(reply(family=4)).is_standard_mf3d)
    def test_invalid_and_unrelated(self):
        self.assertIsNone(decode_identity_reply(bytes.fromhex('F0 00 01 79 02 01 00 03 F7')))
        with self.assertRaises(ValueError):
            decode_identity_reply(bytes.fromhex('F0 00 01 79 05 01 00 F7'))
    def test_no_config_read_without_identity(self):
        b=self.make_backend()
        with self.assertRaises(RuntimeError):b.send_main_config_read_request()
        with self.assertRaises(RuntimeError):b.send_color_read_request(1)
        self.assertFalse(b.output.sent)
    def test_explicit_handshake_then_config_read(self):
        b=self.make_backend();b.request_identity()
        self.assertEqual(b.output.sent,[('sysex',{'data':bytes.fromhex('00 01 79 05')})])
        self.assertIsNone(b.observe_identity(bytes.fromhex('F0 00 01 79 02 01 00 03 F7')))
        with self.assertRaises(RuntimeError):b.send_main_config_read_request()
        self.assertTrue(b.observe_identity(reply()).is_standard_mf3d)
        b.send_main_config_read_request();b.send_color_read_request(1)
        self.assertEqual(b.output.sent[1],('sysex',{'data':bytes.fromhex('00 01 79 02 00')}))
        self.assertEqual(b.output.sent[2],('sysex',{'data':bytes.fromhex('00 01 79 04 01 01')}))
    def test_reject_foreign_model_or_timeout(self):
        b=self.make_backend();b.request_identity()
        self.assertFalse(b.observe_identity(reply(model=3)).is_standard_mf3d)
        with self.assertRaises(RuntimeError):b.send_color_read_request(1)
        b.request_identity();b.expire_identity()
        with self.assertRaises(RuntimeError):b.send_color_read_request(1)
    def test_reconnect_discards_old_identity(self):
        b=self.make_backend();b.request_identity();b.observe_identity(reply())
        self.assertTrue(b.verified_identity.is_standard_mf3d)
        b.disconnect()
        self.assertIsNone(b.verified_identity)
        self.assertFalse(b.identity_pending)
    def test_other_midi_port(self):
        b=self.make_backend();b.output_name='Generic Synth'
        with self.assertRaises(RuntimeError):b.request_identity()
        self.assertEqual(b.output.sent,[])
if __name__=='__main__':unittest.main()
