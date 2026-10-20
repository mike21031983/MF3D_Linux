# CP07 — corrected .mfs on-disk serializer

Date: 2026-10-20. Evidence from the supplied original macOS Utility (disassembly preserved in private recovery).

## Correction of CP06

CP06 mistakenly treated the first two bytes 02 01 as part of the saved .mfs serializer. The actual on-disk block has NO 02 01 header.

- MidiSerializer::dump() at 0x100102440 produces [tag0,value0,tag1,value1,...], as seen near 0x1001024b5–4c5 and 0x10010250c–51f.
- ConfigWidget::buildMfsBlob() at 0x100109990 prepends u16be byte length and appends the raw dump and extension records.
- ConfigWidget::importSettingsFromBlob() at 0x100109e80 constructs a NEW in-memory 02 01 prefix, then appends bytes from the file before passing them to ConfigWidget::sysEx. The original file retains raw pairs.
- ConfigWidget::sysEx() at 0x100104820 handles the prefixed incoming pairs. A normal physical reply clears the previous serializer, but an import with importing flag set does not.

The pair 02 01 may also represent valid data tag=2,value=1; it is not a reliable file signature.

## CP07 changes

- decode_mfs_serializer: reads unframed pairs from file.
- decode_serializer_body: remains separate for live 02 01 SysEx bodies.
- mfs_container: corrected offline inspection of tag/value pairs.
- mfs_backup: binary-preserving backup from .mfs into base64 JSON and guarded restoration to a NEW .mfs file, preserving unknown fields and record order with SHA256 checking.
- Native GUI and research/mfs_tool.py: explicit offline backup and restoration controls, never overwriting existing files.
- Historical CP06 synthetic tests updated, plus new CP07 regressions.

Local checks: 57/57 unit tests PASS, compileall PASS, headless Xvfb GUI PASS. GitHub Actions/runners 0 executions.

## Open issues

There is still no original exported and round-trip-confirmed .mfs sample; synthetic passing tests do not prove compatibility with real exports. Physical controller has not been tested. A verified end-of-configuration signal for hardware 02 01 and safe persistent write path are still missing. EEPROM, reset and firmware-flash commands are not implemented.
