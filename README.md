# MF3D Linux — нативный MIDI Fighter 3D Utility

**Цель:** полная функциональная замена фирменного MIDI Fighter Utility под Linux Mint, без Wine и Windows API.

**Статус CP01 (20.10.2026): прототип, не готовая 1:1 замена.** Уже написаны Linux GUI, MIDI-матрица 4×16, ALSA/RtMidi backend, MIDI-монитор и управление LED цветом/анимациями на основе официального руководства. Пока **не проверено на реальном MIDI Fighter 3D**. Запись постоянных настроек устройства, полный GUI фирменной утилиты и прошивка пока не реализованы.

## Запуск на Linux Mint 21.3

```bash
sudo apt install python3-tk python3-mido python3-rtmidi
python3 -m mf3d_linux
```

Запуск не требует root, драйвера ядра или Wine. Контроллер использует стандартный USB-MIDI, утилита подключается к MIDI IN/OUT через ALSA.

## Статические тесты (не Actions)

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q mf3d_linux
```

На текущем этапе GitHub Actions **ни разу не запускались**. Если в дальнейшем три последовательных запуска упадут, требуется остановить повторы и сначала разобраться в причинах.

## Обратный инжиниринг оригиналов

Пользователь предоставил оригинальные `Midi_Fighter_Utility_OSX.dmg` и `Midi+Fighter+Utility+Win.exe`. macOS DMG разобран до HFS+ и Mach-O; обнаружены Qt, RtMidi, и символы `MidiSerializer::send/read/write`, `ConfigWidget::pushBulkTransfer/pullBulkTransfer`, `Midi::sysEx`. Windows EXE определён как Inno Setup/PE32, извлечение payload ещё не выполнено. Файлы прошивки 3D из DMG не использовались.

Пока полная документация команд persistent SysEx не проверена, в новом Linux коде **нет операций прошивки, factory reset и записи EEPROM**: риск испортить устройство недопустим. MIDI Live LED protocol документирован в руководстве DJ TechTools v1.03.

Исследовательская хронология, оригиналы и инструменты извлечения лежат в частном **recovery ZIP**, не в открытом GitHub. Не публикуйте чужие бинарники и `.hex` в репозитории.

Этот независимый проект не связан с DJ TechTools.
