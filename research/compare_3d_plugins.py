#!/usr/bin/env python3
"""Offline verification of exact vendor MF3D plugin equality (Windows solid stream vs macOS)."""
import argparse,hashlib
from pathlib import Path
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('windows_decompressed_stream')
    ap.add_argument('mac_device_mf_3d_js')
    args=ap.parse_args()
    win=Path(args.windows_decompressed_stream).read_bytes()
    mac=Path(args.mac_device_mf_3d_js).read_bytes()
    if not mac.startswith(b'// DJ Tech Tools\nvar MFR = "000179";'):
        raise ValueError('Unexpected Mac plugin identifier')
    marker=mac[:1024]
    at=win.find(marker)
    if at<0 or win.find(marker,at+1)>=0:raise ValueError('Unique plugin marker missing')
    match=win[at:at+len(mac)]
    print('WINDOWS_OFFSET',at,'PLUGIN_BYTES',len(mac),'MATCH_EXACT',match==mac)
    print('SHA256_WIN',hashlib.sha256(match).hexdigest())
    print('SHA256_MAC',hashlib.sha256(mac).hexdigest())
    if match!=mac:raise SystemExit(1)
if __name__=='__main__':main()
