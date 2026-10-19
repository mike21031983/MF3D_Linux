# CP01 reverse engineering: проверенные результаты

- Пользователь предоставил Windows EXE (28 207 160 байт), macOS DMG (41 753 817 байт).
- Windows: PE32/i386, сигнатура установщика `Inno Setup`, extraction не готов. Не делались выводы о формате Win payload.
- Mac: UDIF (`koly`), zlib-compressed GPT with Apple_HFS partition, восстановлен HFS+ в Python без mount.
- `Midi Fighter Utility.app/Contents/MacOS/Midi Fighter Utility`: Mach-O 64-bit x86_64, 8 689 568 байт.
- Признаки Qt (Info.plist Qt/QMake, Qt widgets) и RtMidi (`RtMidiIn`, `RtMidiOut`).
- Имена функций реально видны в Mach-O LC_SYMTAB: `Midi::sysEx`, `Device::sysEx`, `MidiSerializer::send/read/write/dump`, `ConfigWidget::pushBulkTransfer`, `pullBulkTransfer`, `requestConfig`, `serializerRead/Write`.
- В бинарнике видна семибитная упаковка некоторых полей сериализатора, но общий протокол SysEx и сохранения EEPROM ещё не доказан; НЕ отправлять такие команды до восстановления заголовков/контрольных сумм.
- В DMG находятся два файла firmware с префиксом `3d_` дат 2013 и 2018. Их не запускали и в репозитории не публикуют.
- В User Guide v1.03, стр. 2, явно указано 0-based нумерование MIDI каналов. Стр. 14–17 содержат точные числовые Note IDs банков. Стр. 4–5 и 19 содержат velocity-коды LED, яркости, Gate, Pulse.
- В руководстве есть нестыковки в именах нот и описаниях интервалов, поэтому код использует **числовые Note IDs**, а не текстовые обозначения октав.
- Нативный Linux CP01: простая Tk GUI, mido / RtMidi, без Wine. Реальная проверка с физическим девайсом пока отсутствует.

Следующие задачи: точное восстановление SysEx; safe read-only pull-конфигурации; offline round-trip serializer tests; GUI parity с фирменной программой. Flash только после отдельной верификации совместимости прошивки и протокола.
