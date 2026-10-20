# CP09 — Windows Qt6, offline MIDI transaction inspector

Date 2026-10-20. Sources: the user's original Windows installer (previously extracted Inno solid stream), Mac DMG/disassembly preserved privately in recovery.

## Windows binary evidence

- Carved original PE64 module artifacts/windows_pe/win_module_36_04ae1fac.exe: 8,698,880 bytes, SHA256 22d7dafc3d0589d3dc1e40466ed37d146227d683760ecf90253a7e5f9252a6e8.
- Windows x86_64 PE32+, timestamp header 2026-07-02 (not guaranteed build date). Imports WINMM.dll, Qt6Widgets.dll, Qt6Gui.dll, Qt6Qml.dll, Qt6Network.dll and Qt6Core.dll.
- Strings include Midi Fighter 3D, Midi Fighter Twister and Device::requestDeviceId. This does NOT prove Windows and Mac SysEx implementation are identical.
- Contiguous 00 01 79 05 bytes not found in this PE; the Mac original constructs this SysEx frame in steps, so the absence does not disprove the query. Carved PE may still contain original Inno CALL/JMP preprocessing.
- Previous CP03 evidence proves identical device.mf_3d.js plugin bytes on Win/Mac (field definitions), not equality of platform MIDI transport.

## CP09 software

- mf3d_linux/trace_analysis.py: offline-only JSON trace analysis (<=512 events, <=1 MiB file), correlates outgoing read queries 05, 02 00, 04 01 and incoming identity/configuration/RGB7 responses.
- Identity decoding is provisional from the macOS static disassembly, not yet confirmed by hardware. Main configuration is NEVER marked fully read; previous 02 01 response replaces prior device settings.
- Unverified identity refuses to treat a subsequent configuration or color transfer as a confirmed read. Two color captures are checked independently against 192 RGB7 values and final-marker condition.
- research/inspect_midi_trace.py: pure offline CLI. The optional --report creates only new files. Example: python3 research/inspect_midi_trace.py sample_trace.json
- JSON format: {"format":"MF3D_OFFLINE_TRACE_V1","events":[{"direction":"tx","sysex":"F0 00 01 79 05 F7"}, {"direction":"rx","sysex":"F0 00 01 79 05 01 0B 16 03 00 01 00 01 02 03 04 F7"}]}. These are **SYNTHETIC** bytes, not evidence of a real device response.
- midi_backend.py now uses itertools.islice for polling to avoid allocating the entire pending MIDI queue, capped at 1..1024 events per call.

## Limits / checks

- 79/79 local unit tests PASS, compileall PASS; Xvfb GUI startup PASS. python-rtmidi unavailable in this environment so REAL MIDI/ALSA connection NOT tested.
- GitHub Actions/runners = 0. Physical controller = 0 connections/tests. No persistent write, reset, EEPROM, DFU or flash.
- Raw identity SysEx may include unique device identifiers; never commit raw hardware logs to a public repository.
- CP09 prepares ONE meaningful eventual device session: identify, read settings, read both color blocks, then inspect captured trace offline. The user need not perform repeated interim tests.

Code, research artifacts and chronology are in the private CP09 recovery ZIP; vendor binaries should never enter the public repository.
