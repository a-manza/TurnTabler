# USB Hardware Testing Guide - Behringer UCA202

**Use this guide when your UCA202 hardware arrives.**

This document provides step-by-step validation of USB audio integration before attempting full streaming to Sonos.

---

## Prerequisites

### 1. Install TurnTabler with Dependencies

```bash
cd /home/a_manza/dev/turntabler

# System packages (ALSA development libraries)
sudo apt-get update
sudo apt-get install -y libasound2-dev alsa-utils

# Python dependencies (all included in standard install)
uv pip install -e .
```

### 2. Verify Installation

```bash
python -c "import alsaaudio; print('✅ pyalsaaudio installed')"
python -c "import soco; print('✅ soco installed')"
python -c "import fastapi; print('✅ fastapi installed')"
```

---

## Hardware Connection

### 1. Physical Setup

**Connect in this order:**
1. Plug UCA202 into USB port
2. Connect turntable RCA outputs to UCA202 RCA inputs (red/white)
3. **Important:** Check if turntable has "Phono/Line" switch:
   - If switch exists: Set to "Line" position
   - If no switch and turntable is vintage (pre-2000): You may need external phono preamp

### 2. Verify ALSA Detection

```bash
# List all recording devices
arecord -l

# Expected output (device name may vary):
# card 2: CODEC [USB Audio CODEC], device 0: USB Audio [USB Audio]
#   Subdevices: 1/1
#   Subdevice #0: subdevice #0
```

**✅ Success:** You see "CODEC" or "USB Audio CODEC" listed
**❌ Failure:** Device not shown → Check USB connection, try different USB port

---

## Test Progression (In Order)

### Test 1: Python Device Detection

**Purpose:** Verify Python can find the UCA202

```bash
cd /home/a_manza/dev/turntabler
python -m turntabler.usb_audio
```

**Expected Output:**
```
Available USB audio devices:
  Device: hw:CARD=CODEC,DEV=0
  Name: USB Audio CODEC
  Is Accessible: True

Auto-detected device: hw:CARD=CODEC,DEV=0
✅ USB audio device ready for capture
```

**✅ Success:** Device detected with "Accessible: True"
**❌ Failure:** "Permission denied" → Run: `sudo usermod -a -G audio $USER` then log out/in

---

### Test 2: Raw ALSA Audio Capture

**Purpose:** Verify ALSA can capture audio from UCA202

```bash
# Capture 5 seconds of audio (play music/speak near turntable)
arecord -D hw:CARD=CODEC,DEV=0 -f S16_LE -r 48000 -c 2 -d 5 /tmp/test.wav

# Play back captured audio
aplay /tmp/test.wav
```

**✅ Success:** You hear your audio played back
**❌ Failure:** Silent playback → Check:
1. Input gain too low (run `alsamixer`, press F4 for capture, F6 select CODEC, increase level)
2. Wrong input source (turntable not connected properly)
3. Phono-level signal without preamp (vintage turntable needs external preamp)

---

### Test 3: Python Audio Capture Module

**Purpose:** Verify USBAudioCapture class works

```bash
python -m turntabler.usb_audio_capture
```

**Expected Output:**
```
Starting USB audio capture test...
Configuration:
  Device: hw:CARD=CODEC,DEV=0
  Sample Rate: 48000 Hz
  Channels: 2
  Format: S16_LE
  Period Size: 1024 frames

Capturing 5 seconds of audio...
[Progress updates...]

Capture complete:
  Frames captured: 240000
  Data written: /tmp/turntabler_test_capture.raw
  Buffer overruns: 0

✅ USB audio capture successful
```

**✅ Success:** Capture completes with 0 or few overruns
**❌ Failure:** Many buffer overruns → Increase period_size in config

---

### Test 4: USBAudioSource Integration

**Purpose:** Verify USBAudioSource class initializes

```bash
python -c "
from turntabler.audio_source import USBAudioSource, AudioFormat
source = USBAudioSource(AudioFormat())
print('✅ USBAudioSource initialized successfully')
chunk = source.read_chunk(1024)
print(f'✅ Read {len(chunk)} bytes from USB')
source.close()
print('✅ Closed cleanly')
"
```

**✅ Success:** All three checkmarks appear
**❌ Failure:** Check error message, likely device in use or permissions

---

### Test 5: Short Streaming Test (30 seconds)

**Purpose:** Verify end-to-end streaming with USB source

```bash
# Stream from UCA202 to Sonos for 30 seconds
python -m tests.integration.test_streaming_e2e --source usb --duration 30
```

**Expected Output:**
```
Creating USB audio source
Auto-detected: hw:CARD=CODEC,DEV=0
✅ USB audio source initialized
✅ HTTP server is ready
Discovering Sonos devices...
[...]
✅ Audio is playing!
```

**✅ Success:** Continuous playback for 30 seconds, 0 errors
**❌ Failure:** Audio dropouts → Check system load, USB connection quality

---

### Test 6: Full Validation (10 minutes)

**Purpose:** Validate production-ready performance

```bash
# Full 10-minute streaming test
python -m tests.integration.test_streaming_e2e --source usb --duration 600
```

**Expected Performance:**
- **CPU Usage:** 5-10% (should be similar to synthetic source)
- **Memory:** ~64-80 MB (stable, no growth)
- **Audio Chunks:** ~9,820 chunks (consistent with synthetic)
- **Interruptions:** 0
- **Buffer Overruns:** 0-5 acceptable, >10 needs tuning

**✅ Success:** Matches synthetic source performance
**❌ Needs Tuning:** Adjust ALSA config (period_size, periods) in USBAudioSource

---

## Troubleshooting

### Issue: "No USB audio device found"
**Solutions:**
- Run `arecord -l` to verify ALSA detection
- Try different USB port (preferably USB 2.0 or 3.0)
- Check `dmesg | tail` for USB errors

### Issue: "Permission denied"
**Solutions:**
```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Log out and log back in (or reboot)

# Verify group membership
groups | grep audio
```

### Issue: Silent audio / very low volume
**Solutions:**
```bash
# Open ALSA mixer
alsamixer

# Press F4 (Capture)
# Press F6, select "CODEC" device
# Use arrow keys to increase "Mic" or "Capture" levels to 80-100%
# Press Esc to exit

# Test again with arecord
```

### Issue: Many buffer overruns
**Solutions:**
Edit `src/turntabler/audio_source.py`, USBAudioSource class:
```python
# Increase period_size from 1024 to 2048
period_size=2048,  # ~42ms latency

# Or increase periods from 3 to 4
periods=4
```

### Issue: Turntable output too quiet (phono-level signal)
**Solution:** Your turntable needs a phono preamp
- **Recommended:** Behringer PP400 (~$25-30)
- Connect: Turntable → PP400 → UCA202 → Computer

---

## Success Criteria

✅ **Ready for Production** when all these pass:
1. Device detected automatically
2. 5-second ALSA capture works
3. Python capture module works
4. USBAudioSource initializes
5. 30-second streaming test: 0 errors
6. 10-minute streaming test: <10 buffer overruns, 0 dropouts

---

## Next Steps After Successful Testing

1. **Update CLAUDE.md** with actual performance metrics from Test 6
2. **Create systemd service** for auto-start on Pi
3. **Deploy to Raspberry Pi 5** (if using separate device)
4. **Build CLI application** for production use

---

**Last Updated:** 2025-11-15
**Hardware:** Behringer UCA202 (identical to UCA222)
**Software:** TurnTabler v0.1.0
