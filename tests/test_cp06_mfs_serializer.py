"""CP06: prevent cross-frame pollution and inspect imported .mfs serializer offline."""
import unittest
from mf3d_linux.serializer_capture import decode_mfs_serializer,PassiveSerializerCapture
from mf3d_linux.mfs_container import MfsContainer,Record

class CP06Offline(unittest.TestCase):
    def test_0201_mfs_body(self):
        raw=b'\x00\x03\x07\x01\x63\x25'
        mfs=MfsContainer(raw,(Record(1,1,bytes([0]*192)),Record(2,1,bytes([127]*192))))
        parsed=MfsContainer.parse(mfs.to_bytes())
        self.assertEqual(decode_mfs_serializer(parsed.serializer).pairs,((0,3),(7,1),(99,37)))
        self.assertEqual(parsed.to_bytes(),mfs.to_bytes())
        self.assertIn('tag 99',parsed.describe())
        self.assertIn('192 байта',parsed.describe())
    def test_unknown_mfs_is_lossless(self):
        raw=b'\x88\x99\x01\x02'
        mfs=MfsContainer(raw,(Record(100,3,b'\xff\x8c'),))
        self.assertIn('не распознан',mfs.describe())
        self.assertEqual(MfsContainer.parse(mfs.to_bytes()).serializer,raw)
    def test_invalid_0201(self):
        for raw in (b'',b'\x00',b'\x02\x01\x00',b'\x80\x01'):
            with self.assertRaises(ValueError):decode_mfs_serializer(raw)
    def test_0201_frame_replaces_previous_not_merges(self):
        def frame(t,v):return bytes((0xF0,0,1,121,2,1,t,v,0xF7))
        c=PassiveSerializerCapture()
        c.feed(frame(0,3));c.feed(frame(7,1))
        self.assertEqual(c.values,{7:1})
        self.assertEqual(c.history_values,{0:3,7:1})
        self.assertEqual([x['tag'] for x in c.export()['observed_tags']],[7])
        self.assertEqual(c.export()['status'],'latest_response_only_completion_unverified')
if __name__=='__main__':unittest.main()
