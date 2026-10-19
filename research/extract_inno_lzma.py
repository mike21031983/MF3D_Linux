#!/usr/bin/env python3
"""Offline Inno Setup solid LZMA DATA stream recovery for 2026 MF Utility installer.
Does not execute installer. Does not map filenames; original EXE is required.
Recovered by finding exactly one zlb signature, LZMA1 header, 8 MiB dictionary.
"""
import argparse,lzma
from pathlib import Path
MAGIC=bytes.fromhex('7a6c621a5d00008000')
FILTER=[dict(id=lzma.FILTER_LZMA1,dict_size=8*1024*1024,lc=3,lp=0,pb=2)]
def extract(installer,output,limit=384*1024*1024):
    blob=Path(installer).read_bytes()
    offset=blob.find(MAGIC)
    if offset<0 or blob.find(MAGIC,offset+1)>=0:
        raise ValueError('Expected one LZMA header; refusing to guess')
    cur=offset+len(MAGIC)
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_RAW,filters=FILTER)
    written=0
    with Path(output).open('wb') as out:
        while not decoder.eof and cur<len(blob):
            part=blob[cur:cur+16384]
            cur+=len(part)
            block=decoder.decompress(part,max_length=1048576)
            out.write(block);written+=len(block)
            if written>limit:raise ValueError('Decompression safety limit reached')
            while not decoder.needs_input and not decoder.eof:
                block=decoder.decompress(b'',max_length=1048576)
                out.write(block);written+=len(block)
                if written>limit:raise ValueError('Decompression safety limit reached')
    if not decoder.eof:raise ValueError('No LZMA end marker')
    print(f'LZMA_BEGIN={offset:#x} DECOMPRESSED={written} bytes')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('installer');ap.add_argument('output')
    opts=ap.parse_args();extract(opts.installer,opts.output)
