#!/usr/bin/env python3
"""Offline .mfs inspection, lossless backup and restore. NO hardware interface."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mf3d_linux.mfs_container import MfsContainer
from mf3d_linux.mfs_backup import backup,restore
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=('inspect','backup','restore'))
    ap.add_argument('input')
    ap.add_argument('output',nargs='?')
    args=ap.parse_args()
    if args.action=='inspect':
        print(MfsContainer.from_path(args.input).describe())
        return
    if not args.output:ap.error('New output filename required')
    {'backup':backup,'restore':restore}[args.action](args.input,args.output)
    print('OK:',args.output)
if __name__=='__main__':main()
