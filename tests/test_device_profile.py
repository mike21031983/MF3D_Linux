import tempfile
import unittest
from pathlib import Path
from mf3d_linux.device_profile import Profile,SETTINGS,BY_KEY,encode_color,decode_color,PALETTE
from mf3d_linux.vendor_sysex import parse_sysex

class TestMF3DProfile(unittest.TestCase):
    def test_exact_vendor_tags(self):
        self.assertEqual(len(SETTINGS),17)
        self.assertEqual(BY_KEY['software_mode'].tag,7)
        self.assertEqual(BY_KEY['bank_side_buttons'].tag,23)
        self.assertEqual(BY_KEY['tilt_dead_zone'].minimum,1)
        self.assertEqual(BY_KEY['rotation_range'].maximum,90)
        self.assertEqual(len(PALETTE),20)
    def test_rgb7(self):
        self.assertEqual(encode_color('#FF01EF'),(127,0,119))
        self.assertEqual(decode_color((127,0,119)),'#FE00EE')
        p=Profile()
        p.active[48]='#00FF00'
        raw=p.color_buffer('active')
        self.assertEqual(len(raw),192)
        self.assertEqual(Profile().set_color_buffer('active',raw).active[48],'#00FE00')
    def test_roundtrip(self):
        p=Profile()
        p.settings['software_mode']=1
        p.settings['rotation']=2
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'settings.json'
            p.save(path)
            self.assertEqual(Profile.load(path).as_dict(),p.as_dict())
    def test_reject_invalid(self):
        p=Profile()
        p.settings['tilt_range']=99
        with self.assertRaises(ValueError):p.validate()
    def test_preserve_undocumented_bits(self):
        p=Profile()
        p.animation_reserved=0xC1
        p.settings['motion_animation']=2
        p.settings['button_animation']=5
        self.assertEqual(p.tag10(),0xED)
        p.set_tag10(0xED)
        self.assertEqual(p.tag10(),0xED)

class TestPassiveSysEx(unittest.TestCase):
    def test_vendor(self):
        packet=parse_sysex(bytes.fromhex('F0 00 01 79 04 00 02 01 F7'))
        self.assertTrue(packet.valid_vendor)
        self.assertEqual(packet.category,'bulk-response')
        self.assertEqual(parse_sysex(bytes.fromhex('F0 00 01 79 02 01 F7')).category,'serial-response')
        self.assertFalse(parse_sysex(bytes.fromhex('F0 7D 01 F7')).valid_vendor)
    def test_invalid(self):
        for data in (b'',bytes.fromhex('F0 00 01 79 04 00'),bytes.fromhex('F0 00 01 79 FF F7')):
            with self.assertRaises(ValueError):parse_sysex(data)
if __name__=='__main__':unittest.main()
