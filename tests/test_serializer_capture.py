import unittest
from types import SimpleNamespace
from mf3d_linux.serializer_capture import PassiveSerializerCapture,decode_serializer_reply
def msg(*pairs):
    values=[0,1,0x79,2,1]
    for tag,value in pairs:values.extend((tag,value))
    return SimpleNamespace(type='sysex',data=tuple(values))
class TestCapture(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(decode_serializer_reply(msg((0,3),(99,7))).pairs,((0,3),(99,7)))
    def test_no_false_completion(self):
        c=PassiveSerializerCapture();c.feed(msg((0,3)))
        self.assertIn('partial_observation',c.export()['status'])
        self.assertTrue(c.export()['read_only'])
    def test_other_manufacturer(self):
        self.assertFalse(PassiveSerializerCapture().feed(bytes.fromhex('F0 7D 02 01 00 03 F7')))
    def test_odd_length(self):
        with self.assertRaises(ValueError):
            decode_serializer_reply(bytes.fromhex('F0 00 01 79 02 01 00 F7'))
    def test_conflicting_values(self):
        c=PassiveSerializerCapture();c.feed(msg((7,0)));c.feed(msg((7,1)))
        self.assertEqual(c.conflicts[7],[0,1])
    def test_limit_frames(self):
        c=PassiveSerializerCapture()
        for _ in range(64):c.feed(msg((0,3)))
        with self.assertRaises(ValueError):c.feed(msg((0,3)))
if __name__=='__main__':unittest.main()
