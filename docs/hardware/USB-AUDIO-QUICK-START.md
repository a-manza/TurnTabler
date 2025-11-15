# USB Audio Interface Quick Start Guide

**Quick reference for implementing USB audio capture in TurnTabler**

## Recommended Hardware

### Primary Choice: Behringer UCA222
- **Price:** $30-40
- **Quality:** 16-bit/48kHz (perfect for vinyl)
- **Linux Support:** Excellent (plug-and-play)
- **Additional:** Add Behringer PP400 phono preamp ($25-30) if turntable lacks built-in preamp
- **Total Cost:** $55-70 for complete solution

## Do You Need a Phono Preamp?

### You DON'T need a preamp if:
- Turntable has "Phono/Line" switch (set to Line)
- Turntable has "Line Out" labeled outputs
- Your USB interface has built-in phono preamp

### You DO need a preamp if:
- Turntable only has "Phono Out"
- Turntable is vintage (pre-2000)
- Audio is very quiet without preamp

## Hardware Setup

**With built-in preamp:**
```
Turntable (Line Out) → Behringer UCA222 → USB → Raspberry Pi
```

**Without built-in preamp:**
```
Turntable (Phono Out) → Behringer PP400 → Behringer UCA222 → USB → Raspberry Pi
```

## Software Installation

### 1. Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y libasound2-dev alsa-utils python3-dev
```

### 2. Install Python Package
```bash
cd /home/a_manza/dev/turntabler
uv pip install pyalsaaudio
```

### 3. Verify Device Detection
```bash
# List capture devices
arecord -l

# Test capture (5 seconds)
arecord -D hw:1,0 -f S16_LE -r 48000 -c 2 -d 5 /tmp/test.wav

# Play back
aplay /tmp/test.wav
```

## Python Usage

### Simple Device Detection
```python
from turntabler.usb_audio import detect_usb_audio_device

device = detect_usb_audio_device()
print(device)  # 'hw:CARD=UCA222,DEV=0'
```

### Capture Audio
```python
from turntabler.usb_audio import detect_usb_audio_device
from turntabler.usb_audio_capture import USBAudioCapture, CaptureConfig, SampleFormat

# Detect device
device = detect_usb_audio_device()

# Configure
config = CaptureConfig(
    device=device,
    sample_rate=48000,
    channels=2,
    sample_format=SampleFormat.S16_LE,
    period_size=1024,  # 21ms latency
    periods=3          # USB recommended
)

# Capture
capture = USBAudioCapture(config)
if capture.open():
    try:
        for chunk in capture.capture_stream(duration_seconds=10):
            # Process audio chunks
            print(f"Captured {len(chunk)} bytes")
    finally:
        capture.close()
```

## Recommended Configuration

```python
CaptureConfig(
    sample_rate=48000,      # Hz (matches Sonos)
    channels=2,             # Stereo
    sample_format=SampleFormat.S16_LE,  # 16-bit (Behringer UCA222)
    period_size=1024,       # ~21ms latency
    periods=3               # USB recommended
)
```

## Testing

### Test Device Detection
```bash
cd /home/a_manza/dev/turntabler
python -m turntabler.usb_audio
```

### Test Audio Capture
```bash
cd /home/a_manza/dev/turntabler
python -m turntabler.usb_audio_capture
# Captures 10 seconds to /tmp/turntabler_test_capture.raw
```

## Troubleshooting

### Device Not Found
```bash
# List devices
arecord -l

# Check USB connection
dmesg | grep -i usb | tail -20

# Load USB audio driver
sudo modprobe snd_usb_audio
```

### Permission Denied
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and log back in
```

### Buffer Overruns
Increase period size and/or periods:
```python
config = CaptureConfig(
    period_size=2048,  # Higher = more reliable, more latency
    periods=4
)
```

### Silent Audio
```bash
# Adjust input levels with alsamixer
alsamixer
# Press F4 for capture
# Press F6 to select USB device
# Increase capture level
```

## Next Steps

1. Purchase Behringer UCA222 (+ PP400 if needed)
2. Test hardware with `arecord`
3. Test Python modules
4. Integrate with streaming pipeline
5. Connect to SoCo for Sonos streaming

## Documentation

- **Comprehensive Guide:** `/home/a_manza/dev/turntabler/docs/hardware/usb-audio-interface-guide.md`
- **Device Detection Module:** `/home/a_manza/dev/turntabler/src/turntabler/usb_audio.py`
- **Capture Module:** `/home/a_manza/dev/turntabler/src/turntabler/usb_audio_capture.py`
