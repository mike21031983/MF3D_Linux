# CP08 — MF3D device identification and uncertain config completion

Evidence: user-provided macOS Mach-O and original device.mf_3d.js (offline static analysis; no physical USB traffic).

## Original request and reply

- Device::requestDeviceId (Mach-O 0x10010db30) sends **F0 00 01 79 05 F7**, a read-only identity query. The native app sets a pending flag and starts a 1000 ms Qt timer.
- Device::sysExRouted (0x10010ddb0) accepts manufacturer 00 01 79 followed by **05 01** only while identification is pending. Family/model are tentatively decoded as little-endian uint16 at body offsets 4..5 and 6..7.
- The original source checks >=10 bytes but appears to access through offset 11; our parser rejects bodies smaller than 12 bytes.
- The official device.mf_3d.js identifies standard MF3D as family 0003, model 0001. Other models and firmware variants are NOT interchangeable.
- Interpretations of identity field offsets are STATICALLY inferred, not proven by live captured data; do not claim full hardware parity.

## Linux CP08 implementation

- device_identity.py: standalone bounded read-only identity parser.
- midi_backend.py: requires paired MIDI Fighter IN/OUT ports and prior accepted identity reply family=0003/model=0001 to permit vendor READ operations 02 00 / 04 01.
- GUI has explicitly triggered Identify Model button, three-second UI timeout (deliberately longer than original), and a fail-closed status.
- Disconnecting/reconnecting invalidates identity. Other identities, malformed frames or expiry cannot authorize reads. Live standard MIDI note/CC remains available.
- No configuration writes, EEPROM, firmware update, reset or bootloader operations.

## Completion question

ConfigWidget::sysEx (0x100104820) handles 02 01 tag/value responses and resets its serializer for normal incoming data. No independently established end-of-full-configuration signal was found in this path. The export status remains latest_response_only_completion_unverified; timeouts do not mean completed config.

## Validation

Local CP08: 68 unit PASS, compileall PASS, virtual-X11 GUI PASS. GitHub Actions/runners 0. No physical device tests; identity field layout still subject to verification against the real MF3D.

Research disassembly and proprietary binaries are private in CP08 recovery and are not uploaded to the public GitHub repository.
