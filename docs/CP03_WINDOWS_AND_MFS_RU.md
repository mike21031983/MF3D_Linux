# CP03 — Windows installer / Mac comparison / .mfs

## Windows EXE: proven extraction

User-supplied `Midi+Fighter+Utility+Win.exe`: 28,207,160 bytes, Inno Setup 6.7.0 PE32 bootstrap. Single solid compressed stream begins at **0xF0400** with `7A 6C 62 1A` (Inno zlb) and `5D 00 00 80 00` (LZMA1, dictionary 8 MiB). Recover with `research/extract_inno_lzma.py` using Python `lzma.FORMAT_RAW`, 3/0/2 lc/lp/pb, compressed data starting 0xF0409. The stream decompresses to **90,062,033 bytes**, with correct decoder EOF.

The stream is SOLID: this is NOT yet a reconstructed file directory. PE header validation identifies **37 plausible PE modules** in stream, including the main Qt6 x64 EXE at **0x04AE1FAC** (~8.3 MiB), plus libraries. Main exe's imports: WINMM, Qt6Widgets/Gui/Qml/Network/Core, libc++; embedded RtMidi. Its PE timestamp field says 2026-07-02. The images carved from solid stream are **for static analysis only**, as Inno's CALL/JMP transform may require reversing before execution. No binary from this package was run.

## Direct Windows vs Mac match (strong evidence)

The Windows stream contains original text of `device.mf_3d.js` beginning at byte **87,232,428**, length **49,885** bytes. It is **exactly identical byte-for-byte** to the plugin extracted from the provided Mac DMG.

SHA-256 both:
`81ad526846050fefc698f64e6e9570996d2c89f9ca9946ba0a93f0ec4cc98875`.

Therefore the parameter declarations and RGB palette for **MF3D normal model 0001** match on Windows and Mac. This does not establish equality of platform MIDI transports, firmware updaters or all binary logic.

## Original .mfs container structure from Mach-O disassembly

`ConfigWidget::buildMfsBlob` and `importSettingsFromBlob` implement a container with:

```text
uint16_be serializer_length
bytes serializer[serializer_length]
repeated until EOF:
    uint16_be tag
    uint8 kind
    uint16_be data_length
    bytes payload[data_length]
```

Official `device.mf_3d.js` uses color block tag 1 (inactive) / tag 2 (active), kind 1, and 192 RGB7 components per banked 64-pad state. Other tags are preserved unchanged by the parser. This is a reverse-engineered schema, **not validated against an actual exported .mfs sample** yet.

Implemented `mf3d_linux/mfs_container.py`: parser with bounds checks, offline inspection, byte-identical synthetic round trips; application adds a read-only `.mfs` inspection view. It cannot write device EEPROM, cannot update firmware, and does not yet claim official .mfs import/export compatibility.

## Verified CP03 / next work

- 19 local unit tests passed; Python compileall passed; GitHub Actions and runners **0 launches**.
- Original vendor install files stay inside private recovery only, not in public repo.
- Next: confirm against actual .mfs; recover exact SysEx read frames and reply length/state machine; only then consider hardware read; write/flash remain prohibited.
- User requires stop/save full recovery ZIP around every 20 minutes of active work; no repeated unnecessary user testing. The ZIP includes technical notes and reconstructed context, not a byte-for-byte full export of all chat messages.
