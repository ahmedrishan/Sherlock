# Custom Wake Word Models Directory

Place your custom trained openWakeWord ONNX model files in this directory.

- Target Model File: `sherlock.onnx`
- File Path: `models/sherlock.onnx`

When `sherlock.onnx` is present in this directory, `WakeWordDetector` in `core/wake_word.py` will automatically load and activate your custom "sherlock" wake-word model for real-time local detection.
