#!/usr/bin/env python3
"""Safely carve PE section images from recovered Inno solid data for STATIC analysis only.
Recovered sections may retain Inno CALL/JMP preprocessing; do not execute.
"""
import argparse,re,struct,hashlib
from pathlib import Path
def modules(data):
    for m in re.finditer(b'MZ',data):
        offset=m.start()
        if offset+64>=len(data):continue
        pe_offset=struct.unpack_from('<I',data,offset+60)[0]
        if not 64<=pe_offset<4096 or offset+pe_offset+256>len(data):continue
        if data[offset+pe_offset:offset+pe_offset+4]!=b'PE\0\0':continue
        machine,count=struct.unpack_from('<HH',data,offset+pe_offset+4)
        optional=struct.unpack_from('<H',data,offset+pe_offset+20)[0]
        if machine!=0x8664 or not 1<=count<=30 or not 80<=optional<=300:continue
        base=offset+pe_offset+24+optional
        ends=[]
        for i in range(count):
            sect=base+i*40
            size,ptr=struct.unpack_from('<II',data,sect+16)
            if ptr+size>len(data)-offset:break
            ends.append(ptr+size)
        if len(ends)!=count:continue
        size=max(ends)
        if 8192<=size<=128*1024*1024:yield offset,size
def main():
    ap=argparse.ArgumentParser();ap.add_argument('decompressed_stream');ap.add_argument('output_dir')
    a=ap.parse_args();data=Path(a.decompressed_stream).read_bytes()
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    for n,(offset,size) in enumerate(modules(data)):
        chunk=data[offset:offset+size]
        dest=out/f'win_module_{n:02d}_{offset:08x}.exe'
        dest.write_bytes(chunk)
        print(n,hex(offset),size,hashlib.sha256(chunk).hexdigest())
if __name__=='__main__':main()
