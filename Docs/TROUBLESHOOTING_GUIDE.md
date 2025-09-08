## Troubleshooting Guide

| Symptom | Cause | Solution |
|---|---|---|
| App crashes on startup | Missing .tflite file | Ensure `mobile_lstm.tflite` is in `assets/`. |
| Output is NaN | Incorrect input shape | Verify input is 20 timesteps * 4 features. |
| Slow performance | No quantization | Re-train with `converter.optimizations`. |
| BLE not connecting | Missing permissions | Add BLUETOOTH permissions to Manifest. |
| Emulator not launching | Insufficient RAM | Allocate 4GB RAM to the emulator. |
