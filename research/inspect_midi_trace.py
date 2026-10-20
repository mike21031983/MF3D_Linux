#!/usr/bin/env python3
"""Pure offline vendor MIDI transcript checker. Does not open any MIDI port."""
import sys,argparse,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mf3d_linux.trace_analysis import inspect_file

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trace_json',help='MF3D_OFFLINE_TRACE_V1; may contain hardware identifiers')
    ap.add_argument('--report',help='New JSON output (never overwrite)')
    a=ap.parse_args()
    text=json.dumps(inspect_file(a.trace_json),ensure_ascii=False,indent=2)+'\n'
    if a.report:
        with Path(a.report).open('x',encoding='utf-8') as fd:fd.write(text)
    else:print(text,end='')
if __name__=='__main__':main()
