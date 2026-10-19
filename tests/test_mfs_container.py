import unittest
from mf3d_linux.mfs_container import MfsContainer,Record

class TestMfs(unittest.TestCase):
    def test_binary_roundtrip(self):
        value=b'\x00\x03\x01\x7f\x02'+b'\x00\x01\x01\x00\x02\xfe\xff'+b'\x00\x02\x01\x00\x01\x01'
        parsed=MfsContainer.parse(value)
        self.assertEqual(parsed.serializer,b'\x01\x7f\x02')
        self.assertEqual(parsed.records[0],Record(1,1,b'\xfe\xff'))
        self.assertEqual(parsed.to_bytes(),value)
    def test_two_color_buffers(self):
        raw=bytes(range(128))+bytes(range(64))
        box=MfsContainer(b'\x01'*128,(Record(1,1,raw),Record(2,1,raw)))
        self.assertEqual(MfsContainer.parse(box.to_bytes()),box)
    def test_truncation_rejected(self):
        for data in (b'',b'\x00',b'\x00\x02\x01',b'\x00\x00\x01\x02',
                     b'\x00\x00\x00\x01\x01\x00\x04\x00'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):MfsContainer.parse(data)
    def test_excessive_input_rejected(self):
        with self.assertRaises(ValueError):MfsContainer.parse(b'\x00\x00'+b'X'*1048576)
if __name__=='__main__':unittest.main()
