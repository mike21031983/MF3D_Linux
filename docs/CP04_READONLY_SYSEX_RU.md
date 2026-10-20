# CP04 — read-only SysEx reconstruction (20 October 2026)

## Static evidence from user-provided macOS Utility

- In `ConfigWidget::pullBulkTransfer` at Mach-O address `0x100108d90`, the byte sequence for reading color block tag 1 or 2 is `F0 00 01 79 04 01 TAG F7`. It is a **read request**, not a write/update.
- `ConfigWidget::sysEx` at `0x100104820` checks manufacturer ID `00 01 79` and receives `04 00` bulk frames. After `04 00`, bytes are `TAG, marker_a, marker_b, opaque, data...`. The original app accumulates from data offset 6; equality of the two marker bytes indicates its final fragment condition. **The exact meaning of the two marker bytes and opaque byte has NOT been confirmed using device traffic.**
- The original source module `device.mf_3d.js` uses tag 1 = inactive LED colors, tag 2 = active; 64 buttons × 3 RGB7 components = 192 bytes per block.
- `ConfigWidget::serializerRead` at `0x100104700` only reads a **local MidiSerializer**. `requestConfig` at `0x10010acd0` only schedules a Qt callback `configuration_loaded`; it is **not** a SysEx query.

## CP04 implementation

- `bulk_read.py` produces allowlisted read frames and passively decodes replies, with strict 7-bit and length bounds; no device transmission on import.
- `color_read_session.py`: staged capture of 1 then 2, timeouts, no partial snapshots on failure.
- `midi_backend.py`: `send_color_read_request(tag)` requires an explicitly connected output whose name contains “MIDI Fighter”, and only permits tag 1/2.
- `app.py`: explicit experimental read-only button, second block automatically requested after complete first, independent JSON export of color buffers only, never claiming all settings were read.
- Synthetic unit tests and headless GUI checks: **35 tests PASS in local CP04 recovery**. Main GitHub tree can differ in file formatting from recovery tree inherited from CP03. GitHub Actions/runners: **0**.

## Not implemented or established

- The actual controller has **not been attached**; the two-block hardware read is therefore experimental and not verified.
- The exact fragmentation/retry/ack flow for all firmware revisions is not yet validated.
- The persistent configuration fields (the serializer) are not yet read from hardware.
- **Never** use firmware update, factory reset or EEPROM write. Offline imports and synthesized examples are not evidence of device compatibility.
- Keep the vendor EXE/DMG/plugins only in private recovery ZIP, not the public repository.

Next: reverse engineer `MidiSerializer::send` read protocol and configuration response without device writes, extend offline tests, preserve original unknown fields. User does not need to perform interim tests. Create recovery ZIP around each 20-minute milestone, including source and chronology.
