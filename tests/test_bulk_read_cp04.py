"""CP04 tests with simulated vendor frames; no physical hardware."""
import unittest
from types import SimpleNamespace
from mf3d_linux.bulk_read import build_bulk_read_request,decode_bulk_reply,ColorBulkCapture
from mf3d_linux.color_read_session import ColorReadSession
def reply(tag,a,b,values,opaque=0):
    return SimpleNamespace(type='sysex',data=(0,1,0x79,4,0,tag,a,b,opaque,*values))
class ReadTests(unittest.TestCase):
    def test_original_wire_bytes(self):
        self.assertEqual(build_bulk_read_request(1).hex(' '),'f0 00 01 79 04 01 01 f7')
        self.assertEqual(build_bulk_read_request(2).hex(' '),'f0 00 01 79 04 01 02 f7')
    def test_allowlist(self):
        for v in (-1,0,3,True,127,'1'):
            with self.assertRaises(ValueError):build_bulk_read_request(v)
    def test_header(self):
        f=decode_bulk_reply(reply(1,2,3,[12,18],opaque=7))
        self.assertEqual((f.tag,f.marker_a,f.marker_b,f.opaque,f.values),(1,2,3,7,(12,18)))
        self.assertFalse(f.final_marker)
    def test_reject_short(self):
        with self.assertRaises(ValueError):
            decode_bulk_reply(bytes.fromhex('f0 00 01 79 04 00 01 01 f7'))
    def test_other_message_is_ignored(self):
        self.assertIsNone(decode_bulk_reply(bytes.fromhex('f0 00 01 79 04 01 01 f7')))
    def test_192_bytes(self):
        capture=ColorBulkCapture(1)
        self.assertFalse(capture.feed(reply(2,0,0,[1]*24)))
        for i in range(8):capture.feed(reply(1,i,7,[i]*24))
        self.assertTrue(capture.complete)
        self.assertEqual(len(capture.get_values()),192)
    def test_early_end(self):
        c=ColorBulkCapture(2)
        with self.assertRaises(ValueError):c.feed(reply(2,0,0,[0]*24))
    def test_two_buffer_session(self):
        s=ColorReadSession();s.begin(0)
        for i in range(8):response=s.feed(reply(1,i,7,[i]*24),i/10)
        self.assertEqual(response,build_bulk_read_request(2))
        for i in range(8):s.feed(reply(2,i,7,[i+8]*24),1+i/10)
        self.assertEqual(s.state,'complete')
        self.assertEqual(len(s.snapshot()[2]),192)
    def test_timeout_discards_partial(self):
        s=ColorReadSession(timeout_seconds=1);s.begin(2)
        self.assertTrue(s.expire(3))
        self.assertEqual(s.state,'failed')
        self.assertEqual(s.results,{})
    def test_no_implicit_port(self):
        s=ColorReadSession()
        self.assertEqual(s.state,'idle')
        self.assertIsNone(s.active)
if __name__=='__main__':unittest.main()
