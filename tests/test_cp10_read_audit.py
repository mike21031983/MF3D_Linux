"""CP10 one-shot READ transaction tests. Offline synthetic MIDI ONLY."""
import tempfile,unittest,json
from pathlib import Path
from mf3d_linux.read_audit import AuditSession
from mf3d_linux.trace_analysis import inspect

def identity(model=1):return bytes((0xF0,0,1,0x79,5,1,11,22,3,0,model,0,1,2,3,4,0xF7))
def settings():return bytes.fromhex('F0 00 01 79 02 01 00 03 07 01 F7')
def bulk(tag,index):
    return bytes((0xF0,0,1,0x79,4,0,tag,index,7,0,*([tag+index]*24),0xF7))

class TestReadAudit(unittest.TestCase):
    def test_one_shot_and_offline_replay(self):
        s=AuditSession();self.assertEqual(s.begin(0).hex(),'f000017905f7')
        self.assertEqual(s.feed(identity(),0.1).hex(),'f00001790200f7')
        self.assertEqual(s.feed(settings(),0.2).hex(),'f0000179040101f7')
        for tag in (1,2):
            for index in range(8):
                query=s.feed(bulk(tag,index),0.3+(tag-1)*.3+index/100)
                if tag==1 and index==7:self.assertEqual(query.hex(),'f0000179040102f7')
                else:self.assertIsNone(query)
        report=s.report()
        self.assertTrue(report['led_colors_complete'])
        self.assertFalse(report['main_settings_complete'])
        self.assertEqual(len(report['inactive_rgb7']),192)
        replay=inspect(s.trace_document()['events'])
        self.assertTrue(replay['colors']['1']['complete'])
        self.assertTrue(replay['colors']['2']['complete'])
        with tempfile.TemporaryDirectory() as folder:
            r=Path(folder)/'audit.json';t=Path(folder)/'trace.json'
            s.save_report(r);s.save_trace(t)
            self.assertEqual(json.loads(r.read_text())['status'],'colors_complete_settings_unverified')
            self.assertEqual(len(json.loads(t.read_text())['events']),22)
            with self.assertRaises(FileExistsError):s.save_report(r)
    def test_foreign_model_fails_without_settings(self):
        s=AuditSession();s.begin(0)
        self.assertIsNone(s.feed(identity(model=2),0.1))
        self.assertEqual(s.phase,'failed')
        self.assertEqual(len(s.trace_document()['events']),2)
    def test_identity_timeout(self):
        s=AuditSession();s.begin(0);s.tick(3)
        self.assertEqual(s.phase,'failed')
        self.assertEqual(len(s.trace),1)
    def test_missing_settings_allowed_but_flagged(self):
        s=AuditSession();s.begin(0);s.feed(identity(),.1)
        self.assertEqual(s.tick(4.2).hex(),'f0000179040101f7')
        for tag in (1,2):
            for i in range(8):s.feed(bulk(tag,i),4.3+(tag-1)*.3+i/100)
        self.assertEqual(s.phase,'finished')
        self.assertIsNone(s.report()['main_settings'])
        self.assertTrue(s.report()['warnings'])
    def test_partial_colors_discarded(self):
        s=AuditSession();s.begin(0);s.feed(identity(),.1);s.feed(settings(),.2)
        s.feed(bulk(1,0),.3);s.tick(4.3)
        self.assertEqual(s.phase,'failed')
        self.assertIsNone(s.report()['inactive_rgb7'])
    def test_no_auto_transmit(self):
        s=AuditSession()
        with self.assertRaises(RuntimeError):s.report()
        s.begin(0)
        with self.assertRaises(RuntimeError):s.report()
        self.assertEqual(s.trace[0]['direction'],'tx')
    def test_invalid_message(self):
        s=AuditSession();s.begin(0)
        with self.assertRaises(ValueError):s.feed(b'not sysEx',.1)
        self.assertEqual(s.phase,'identity')
if __name__=='__main__':unittest.main()
