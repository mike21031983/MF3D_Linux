import unittest
from types import SimpleNamespace
from mf3d_linux import protocol as p

class TestProtocol(unittest.TestCase):
    def test_all_four_banks(self):
        for bank in range(4):
            expected=[36+16*bank+(3-row)*4+col for row in range(4) for col in range(4)]
            self.assertEqual([p.note_for_pad(bank,i) for i in range(16)],expected)
            for i,num in enumerate(expected):self.assertEqual(p.pad_for_note(bank,num),i)
    def test_command(self):
        self.assertEqual(p.color(0,0,13),p.MidiCommand('note_on',3,48,13))
        self.assertEqual(p.animation(3,15,39),p.MidiCommand('note_on',4,87,39))
        self.assertEqual(p.switch_bank(2),p.MidiCommand('note_on',4,2,127))
    def test_validation(self):
        for bank,pad in [(-1,0),(4,0),(0,-1),(0,16)]:
            with self.assertRaises(ValueError):p.note_for_pad(bank,pad)
        with self.assertRaises(ValueError):p.color(0,0,128)
    def test_monitor(self):
        ev=SimpleNamespace(type='note_on',channel=3,note=48,velocity=127)
        self.assertIn('Пэд 1:',p.describe_incoming(ev))
        ev=SimpleNamespace(type='sysex')
        self.assertIn('SysEx',p.describe_incoming(ev))
if __name__=='__main__':unittest.main()
