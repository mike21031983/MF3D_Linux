"""Purely synthetic CP09 transcript tests, without physical MIDI ports."""
import unittest
from mf3d_linux.trace_analysis import inspect,decode_hex
def tx(x):return {'direction':'tx','sysex':x}
def rx(x):return {'direction':'rx','sysex':x}
def identity(model=1):
    return 'F0 00 01 79 05 01 0B 16 03 00 %02X 00 01 02 03 04 F7'%model
def bulk(tag,index,final=False):
    vals=('01 '*24).strip()
    return 'F0 00 01 79 04 00 %02X %02X 07 00 %s F7'%(tag,7 if final else index,vals)
class TraceTests(unittest.TestCase):
    def test_request_identity_and_settings(self):
        r=inspect([tx('F0 00 01 79 05 F7'),rx(identity()),
                   tx('F0 00 01 79 02 00 F7'),rx('F0 00 01 79 02 01 00 03 07 01 F7')])
        self.assertTrue(r['identity']['standard_mf3d'])
        self.assertEqual(r['settings']['latest_pairs'],2)
        self.assertIn('unverified',r['settings']['status'])
    def test_two_led_blocks(self):
        events=[tx('F0 00 01 79 05 F7'),rx(identity())]
        for tag in (1,2):
            events.append(tx('F0 00 01 79 04 01 %02X F7'%tag))
            for i in range(8):events.append(rx(bulk(tag,i,final=i==7)))
        r=inspect(events)
        self.assertTrue(r['colors']['1']['complete'])
        self.assertTrue(r['colors']['2']['complete'])
        self.assertEqual(r['colors']['2']['received_values'],192)
    def test_foreign_model_blocked(self):
        r=inspect([tx('F0 00 01 79 05 F7'),rx(identity(2)),
                   tx('F0 00 01 79 02 00 F7')])
        self.assertFalse(r['identity']['standard_mf3d'])
        self.assertFalse(r['settings']['requested'])
        self.assertTrue(r['warnings'])
    def test_new_identity_invalidates_old(self):
        r=inspect([tx('F0 00 01 79 05 F7'),rx(identity()),
                   tx('F0 00 01 79 02 00 F7'),rx('F0 00 01 79 02 01 00 03 F7'),
                   tx('F0 00 01 79 05 F7')])
        self.assertIsNone(r['identity'])
        self.assertEqual(r['settings']['latest_pairs'],0)
    def test_incomplete_color(self):
        r=inspect([tx('F0 00 01 79 05 F7'),rx(identity()),
                   tx('F0 00 01 79 04 01 01 F7'),rx(bulk(1,0,True))])
        self.assertFalse(r['colors']['1']['complete'])
        self.assertEqual(r['statistics']['errors'],1)
    def test_bad_frames(self):
        for x in ('','00','F0 00 01 79 02 00','F0 00 01 79 82 F7',None):
            with self.subTest(x=x):
                with self.assertRaises(ValueError):decode_hex(x)
    def test_unknown_outgoing(self):
        self.assertIn('unrecognized outgoing',inspect([tx('F0 00 01 79 03 07 F7')])['warnings'][0])
    def test_limit(self):
        with self.assertRaises(ValueError):inspect([tx('F0 00 01 79 05 F7')]*513)
if __name__=='__main__':unittest.main()
