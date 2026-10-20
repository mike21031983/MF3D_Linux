"""CP07 tests based on original dump/import paths; no actual MIDI hardware."""
import tempfile
import unittest
from pathlib import Path
from mf3d_linux.mfs_container import MfsContainer,Record
from mf3d_linux.serializer_capture import decode_mfs_serializer,encode_mfs_serializer,decode_serializer_body
from mf3d_linux.mfs_backup import backup,restore,to_document,from_document
class OfflineMFSCP07(unittest.TestCase):
    def test_unframed_tag_values(self):
        raw=b'\x00\x03\x07\x01\x63\x25'
        self.assertEqual(decode_mfs_serializer(raw).pairs,((0,3),(7,1),(99,37)))
        self.assertEqual(decode_serializer_body(b'\x02\x01'+raw).pairs,decode_mfs_serializer(raw).pairs)
        self.assertEqual(encode_mfs_serializer(((0,3),(7,1),(99,37))),raw)
        self.assertEqual(MfsContainer(raw,()).to_bytes(),b'\x00\x06'+raw)
    def test_0201_can_be_real_first_tag_pair_not_header(self):
        self.assertEqual(decode_mfs_serializer(b'\x02\x01\x00\x03').pairs,((2,1),(0,3)))
    def test_binary_preserved_with_unknown_tags(self):
        obj=MfsContainer(b'\x00\x03\x7f\x40',(
            Record(999,42,b'\xff\x00\x80'),
            Record(1,1,bytes([0]*192)),Record(2,1,bytes([127]*192))))
        doc=to_document(obj)
        self.assertEqual(doc['serializer_preview_only'],[{'tag':0,'value':3},{'tag':127,'value':64}])
        self.assertEqual(from_document(doc).to_bytes(),obj.to_bytes())
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'old.mfs';dst=Path(d)/'new.mfs';backupfile=Path(d)/'backup.json'
            src.write_bytes(obj.to_bytes())
            backup(src,backupfile)
            restore(backupfile,dst)
            self.assertEqual(src.read_bytes(),dst.read_bytes())
            with self.assertRaises(FileExistsError):restore(backupfile,dst)
    def test_sha256_guard(self):
        doc=to_document(MfsContainer(b'\x00\x01',()))
        doc['serializer_b64']='AAI='
        with self.assertRaises(ValueError):from_document(doc)
    def test_invalid(self):
        doc=to_document(MfsContainer(b'\x00\x01',()))
        for value in (128,True,None,'-x'):
            with self.subTest(value=value):
                bad=dict(doc);bad['serializer_b64']=value
                with self.assertRaises(ValueError):from_document(bad)
        for data in (b'',b'\x00',b'\x80\x01',b'\x00\x01\x02',bytes([1,1])*129):
            with self.subTest(data=data[:5]):
                with self.assertRaises(ValueError):decode_mfs_serializer(data)
if __name__=='__main__':unittest.main()
