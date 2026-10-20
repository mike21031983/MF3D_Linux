"""Bounded MIDI queue handling. No hardware or RtMidi required."""
import unittest
from mf3d_linux.midi_backend import MidiBackend
class FakeInput:
    def __init__(self):self.polled=0
    def iter_pending(self):
        for n in range(1000000):
            self.polled+=1
            yield n
class BackendLimitTests(unittest.TestCase):
    def test_poll_only_limit(self):
        b=MidiBackend();b.input=FakeInput()
        self.assertEqual(b.poll(3),[0,1,2])
        self.assertEqual(b.input.polled,3)
    def test_max_count(self):
        b=MidiBackend();b.input=FakeInput()
        self.assertEqual(len(b.poll(1024)),1024)
        self.assertEqual(b.input.polled,1024)
    def test_invalid_limit(self):
        b=MidiBackend();b.input=FakeInput()
        for val in (0,-1,1025,True,1.1):
            with self.subTest(value=val):
                with self.assertRaises(ValueError):b.poll(val)
if __name__=='__main__':unittest.main()
