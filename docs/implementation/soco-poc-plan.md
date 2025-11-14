# SoCo Continuous Streaming POC - Complete Guide

**Date:** 2025-11-14
**Purpose:** Validate that SoCo can stream continuous audio (like turntable) to Sonos Beam with lossless quality
**Time estimate:** 2-3 hours total

---

## Objective

Prove that we can stream continuous, indefinite-length audio from Linux to Sonos Beam using:
- **SoCo** (Python library for Sonos control)
- **FastAPI** (HTTP streaming server)
- **FLAC** (lossless audio codec)

This validates the core mechanism before investing in full implementation.

---

## Success Criteria

**The POC succeeds if:**
- ✅ Audio plays continuously on Sonos Beam
- ✅ Stream runs for 10+ minutes without dropouts
- ✅ Latency < 2 seconds (acceptable for turntable)
- ✅ Audio quality is good (no compression artifacts)
- ✅ Can stop and restart stream

**If all criteria met:** Proceed with SoCo approach (lossless FLAC)
**If criteria fail:** Fall back to OwnTone (proven, but lossy AAC-LC)

---

## Part 1: Environment Setup

### Prerequisites

- Ubuntu 22.04 (or similar Linux)
- Python 3.8+ (will use 3.13 for real implementation)
- Sonos Beam on same network
- Network connectivity between machine and Sonos

### Install Dependencies

```bash
cd /home/a_manza/dev/turntabler

# Create POC directory
mkdir -p poc/soco-test
cd poc/soco-test

# Create virtual environment (using system Python for now)
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install soco fastapi uvicorn numpy soundfile

# Install system packages for audio
sudo apt install ffmpeg sox
```

### Verify Sonos Discovery

```bash
# Quick test that SoCo can find Sonos Beam
python3 -c "from soco import discover; print([d.player_name for d in discover()])"
```

**Expected output:** `['Beam', ...]` (or your Sonos device name)

---

## Part 2: Audio Source Options

Choose ONE of these three options for POC testing:

### Option A: Looping Audio File (Simplest) ⭐ RECOMMENDED

**Pros:** Simple, no dependencies, easy to verify quality
**Cons:** Requires audio file

**Setup:**
```bash
# Generate 30-second test audio (sine wave at 440Hz)
ffmpeg -f lavfi -i "sine=frequency=440:duration=30" \
  -ar 48000 -ac 2 -sample_fmt s24 \
  -c:a flac test-loop.flac
```

**Code:** See `streaming_server_loop.py` below

---

### Option B: Generated Audio (Pure Python)

**Pros:** No external files, good for testing
**Cons:** Requires numpy/soundfile

**Code:** See `streaming_server_generated.py` below

---

### Option C: Web Radio Proxy (Most Realistic)

**Pros:** Tests real-world continuous streaming
**Cons:** More complex, requires internet

**Code:** See `streaming_server_radio.py` below

---

## Part 3: FastAPI Streaming Server Code

Create these files in `/home/a_manza/dev/turntabler/poc/soco-test/`:

### Option A: streaming_server_loop.py

```python
"""
FastAPI server that loops a FLAC file infinitely
Simulates turntable continuous audio stream
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
from pathlib import Path

app = FastAPI()

AUDIO_FILE = Path(__file__).parent / "test-loop.flac"

@app.get("/turntable.flac")
async def stream_turntable():
    """Stream looping FLAC file - simulates endless turntable audio"""

    async def generate():
        """Generator that loops audio file indefinitely"""
        chunk_size = 4096

        while True:  # Infinite loop
            try:
                with open(AUDIO_FILE, 'rb') as f:
                    # Read FLAC header once
                    header = f.read(chunk_size)
                    yield header

                    # Stream rest of file
                    while chunk := f.read(chunk_size):
                        yield chunk
                        await asyncio.sleep(0.001)  # Prevent blocking

                # File finished, loop back (no gap in audio)
                print("♻️  Looping audio file...")

            except Exception as e:
                print(f"❌ Error streaming: {e}")
                break

    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "none",
            # Fake huge content length for continuous stream
            "Content-Length": "999999999999"
        }
    )

@app.get("/")
async def root():
    return {
        "status": "TurnTabler POC Streaming Server",
        "stream_url": "/turntable.flac"
    }

if __name__ == "__main__":
    import uvicorn
    print("🎵 Starting streaming server on http://0.0.0.0:8000")
    print("📻 Stream URL: http://0.0.0.0:8000/turntable.flac")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### Option B: streaming_server_generated.py

```python
"""
FastAPI server that generates audio on-the-fly
Simulates turntable with synthesized test tones
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import numpy as np
import soundfile as sf
import io
import asyncio

app = FastAPI()

SAMPLE_RATE = 48000
CHANNELS = 2

def generate_tone(frequency=440, duration=1.0):
    """Generate sine wave tone"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)

    # Stereo sine wave
    tone = np.sin(frequency * 2 * np.pi * t)
    stereo = np.column_stack([tone, tone])

    return stereo.astype(np.float32)

@app.get("/turntable.flac")
async def stream_turntable():
    """Stream generated audio - simulates turntable"""

    async def generate():
        """Generator that creates FLAC audio on-the-fly"""

        # Generate 5-second chunks indefinitely
        chunk_duration = 5.0
        frequencies = [440, 523, 587, 659, 698]  # A, C, D, E, F
        freq_idx = 0

        while True:
            try:
                # Generate audio chunk
                frequency = frequencies[freq_idx % len(frequencies)]
                audio_data = generate_tone(frequency, chunk_duration)

                # Encode to FLAC in memory
                buffer = io.BytesIO()
                sf.write(buffer, audio_data, SAMPLE_RATE, format='FLAC', subtype='PCM_24')
                buffer.seek(0)

                # Stream FLAC chunk
                flac_data = buffer.read()
                yield flac_data

                print(f"🎵 Generated {chunk_duration}s @ {frequency}Hz")
                freq_idx += 1

                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"❌ Error generating audio: {e}")
                break

    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Content-Length": "999999999999"
        }
    )

@app.get("/")
async def root():
    return {"status": "TurnTabler POC - Generated Audio"}

if __name__ == "__main__":
    import uvicorn
    print("🎵 Starting audio generation server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Part 4: SoCo Control Script

Create `test_soco.py`:

```python
"""
SoCo control script - tells Sonos Beam to play our stream
"""

from soco import discover
import socket
import time

def get_my_ip():
    """Get this machine's IP address on local network"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just for getting local IP
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    print("🔍 Discovering Sonos devices...")
    devices = discover(timeout=5)

    if not devices:
        print("❌ No Sonos devices found!")
        print("   Check network connection and ensure Sonos is on same subnet")
        return

    # List all devices
    print(f"✅ Found {len(devices)} device(s):")
    for d in devices:
        print(f"   - {d.player_name} ({d.ip_address})")

    # Find Beam (or use first device)
    beam = next((d for d in devices if 'Beam' in d.player_name), list(devices)[0])
    print(f"\n🎯 Using device: {beam.player_name}")

    # Build stream URL
    my_ip = get_my_ip()
    stream_url = f'http://{my_ip}:8000/turntable.flac'

    print(f"\n📻 Stream URL: {stream_url}")
    print(f"🎵 Starting playback...")

    try:
        # Play the stream with force_radio for continuous playback
        beam.play_uri(
            stream_url,
            title='TurnTabler POC Test',
            force_radio=True  # CRITICAL: Treats as radio/continuous stream
        )

        print("✅ Stream started successfully!")

        # Wait a moment, then check status
        time.sleep(2)

        info = beam.get_current_transport_info()
        print(f"\n📊 Playback status: {info['current_transport_state']}")

        track_info = beam.get_current_track_info()
        print(f"🎵 Current track: {track_info['title']}")

        print("\n✅ POC TEST RUNNING")
        print("   Listen to your Sonos Beam for audio")
        print("   Let it run for 10+ minutes to test stability")
        print("   Press Ctrl+C to stop when done")

        # Keep script running so we can observe
        while True:
            time.sleep(60)
            status = beam.get_current_transport_info()['current_transport_state']
            print(f"⏱️  Status after {int(time.time())}s: {status}")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping playback...")
        beam.stop()
        print("✅ Playback stopped")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure FastAPI server is running")
        print("   2. Check firewall allows port 8000")
        print(f"   3. Verify stream accessible: curl http://{my_ip}:8000/")

if __name__ == "__main__":
    main()
```

---

## Part 5: Testing Procedure

### Step 1: Start Streaming Server

In terminal 1:

```bash
cd /home/a_manza/dev/turntabler/poc/soco-test
source venv/bin/activate

# Choose your audio source option:
python streaming_server_loop.py    # Option A (recommended)
# OR
# python streaming_server_generated.py  # Option B
```

**Expected output:**
```
🎵 Starting streaming server on http://0.0.0.0:8000
📻 Stream URL: http://0.0.0.0:8000/turntable.flac
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Step 2: Verify Stream Accessible

In terminal 2:

```bash
# Test HTTP endpoint
curl -I http://localhost:8000/turntable.flac

# Should see:
# HTTP/1.1 200 OK
# content-type: audio/flac
```

**Optional: Listen to stream on computer**

```bash
# Play stream locally to verify audio
ffplay http://localhost:8000/turntable.flac
# Should hear tone/music
```

---

### Step 3: Run SoCo Control Script

In terminal 2 (same as above):

```bash
cd /home/a_manza/dev/turntabler/poc/soco-test
source venv/bin/activate

python test_soco.py
```

**Expected output:**
```
🔍 Discovering Sonos devices...
✅ Found 1 device(s):
   - Beam (192.168.86.63)

🎯 Using device: Beam
📻 Stream URL: http://192.168.86.XX:8000/turntable.flac
🎵 Starting playback...
✅ Stream started successfully!
📊 Playback status: PLAYING
```

---

### Step 4: Validate Playback

**Listen to Sonos Beam:**
- Should hear audio playing
- Audio should be continuous (no gaps)
- Quality should sound good (lossless FLAC)

**Let it run for 10+ minutes:**
- Monitor for dropouts
- Check for any interruptions
- Observe server terminal for errors

---

### Step 5: Measure Latency (Optional)

Create `measure_latency.sh`:

```bash
#!/bin/bash
# Simple latency measurement

echo "🕐 Measuring latency..."
echo "   Play a distinctive sound (click, beep) from stream"
echo "   Use phone to record server audio output + Sonos output"
echo "   Compare timestamps in audio editor"
echo ""
echo "Acceptable: < 2 seconds for turntable use case"
```

**Manual method:**
1. Generate distinctive audio (single beep)
2. Record server output and Sonos output simultaneously
3. Compare timing in Audacity or similar
4. Calculate delay

---

## Part 6: Results Documentation

### Fill out this template after testing:

```markdown
# SoCo POC Test Results

**Date:** ___________
**Duration:** ___ minutes tested

## Test Environment
- Ubuntu version: 22.04
- Python version: ___
- SoCo version: ___
- Sonos Beam IP: 192.168.86.63
- Audio source used: [ ] Loop [ ] Generated [ ] Radio

## Results

### 1. Stream Establishment
- [ ] Stream started successfully
- [ ] Sonos began playing within 5 seconds
- [ ] No errors in server logs
- Issues: ___________

### 2. Audio Quality
- [ ] Audio sounds clear (no artifacts)
- [ ] No compression/quality loss detected
- [ ] Volume appropriate
- Quality rating: [ ] Excellent [ ] Good [ ] Fair [ ] Poor
- Issues: ___________

### 3. Stream Stability (10+ minute test)
- Minutes tested: ___
- [ ] No dropouts
- [ ] No buffering pauses
- [ ] Continuous playback
- Stability rating: [ ] Stable [ ] Occasional issues [ ] Frequent issues
- Issues: ___________

### 4. Latency
- Measured latency: ___ ms (or N/A if not measured)
- [ ] Acceptable (< 2 seconds)
- Method: ___________

### 5. Control
- [ ] Can start stream via SoCo
- [ ] Can stop stream via SoCo
- [ ] Can restart stream
- Issues: ___________

## Overall Assessment

**Does POC succeed? [ ] YES [ ] NO**

**Confidence to proceed with SoCo:** ___/10

**Recommendation:**
[ ] ✅ Proceed with SoCo implementation (lossless FLAC)
[ ] ❌ Fall back to OwnTone (proven, but lossy AAC-LC)

**Reasoning:**
___________

## Issues Encountered

List any problems and how they were resolved:
1. ___________
2. ___________

## Next Steps

If POC successful:
- [ ] Set up Python 3.13 + uv environment
- [ ] Implement full SoCo backend
- [ ] Add USB audio capture
- [ ] Create CLI interface

If POC failed:
- [ ] Document failure reasons
- [ ] Begin OwnTone installation
- [ ] Accept AAC-LC quality limitation
```

---

## Part 7: Troubleshooting Guide

### Issue 1: "No Sonos devices found"

**Symptoms:** SoCo discover() returns empty list

**Solutions:**
```bash
# Check Sonos is on network
ping 192.168.86.63

# Check mDNS discovery working
avahi-browse -a | grep -i sonos

# Try specifying IP directly
python3 -c "from soco import SoCo; s = SoCo('192.168.86.63'); print(s.player_name)"

# Check firewall
sudo ufw status
# May need: sudo ufw allow from 192.168.86.0/24
```

---

### Issue 2: "Illegal MIME-Type" Error

**Symptoms:** Sonos won't play stream, error 714

**Solutions:**
1. Try `x-rincon-mp3radio://` prefix instead of `http://`:
   ```python
   stream_url = f'x-rincon-mp3radio://{my_ip}:8000/turntable.flac'
   ```

2. Change MIME type in FastAPI:
   ```python
   media_type="audio/x-flac"  # Instead of "audio/flac"
   ```

3. Add more headers:
   ```python
   headers={
       "Content-Type": "audio/flac",
       "icy-name": "Turntable",
       "icy-genre": "Vinyl"
   }
   ```

---

### Issue 3: Stream Starts Then Stops

**Symptoms:** Audio plays briefly, then silence

**Solutions:**

1. Check server logs for errors
2. Verify file is valid FLAC:
   ```bash
   ffprobe test-loop.flac
   ```

3. Test stream continuity:
   ```bash
   # Stream should run indefinitely
   curl http://localhost:8000/turntable.flac | ffplay -
   ```

4. Increase chunk size:
   ```python
   chunk_size = 8192  # or 16384
   ```

---

### Issue 4: Sonos Can't Reach Server

**Symptoms:** Connection timeout, unreachable

**Solutions:**
```bash
# Check server is accessible from network
# On another device:
curl http://YOUR_IP:8000/

# Check firewall
sudo ufw allow 8000/tcp

# Verify server binding to 0.0.0.0, not 127.0.0.1
# In uvicorn.run(): host="0.0.0.0"

# Check IP address is correct
ip addr show
```

---

### Issue 5: Poor Audio Quality

**Symptoms:** Compression artifacts, quality loss

**Solutions:**

1. Verify FLAC encoding:
   ```python
   # In soundfile.write():
   format='FLAC', subtype='PCM_24'
   ```

2. Check sample rate:
   ```python
   SAMPLE_RATE = 48000  # Not 44100 or lower
   ```

3. Use Wireshark to verify FLAC:
   ```bash
   sudo tcpdump -i any -w stream.pcap 'host 192.168.86.63'
   # Analyze in Wireshark, check for FLAC headers
   ```

---

## Part 8: Quick Start Summary

For the impatient, here's the TL;DR:

```bash
# 1. Setup
cd /home/a_manza/dev/turntabler
mkdir -p poc/soco-test && cd poc/soco-test
python3 -m venv venv && source venv/bin/activate
pip install soco fastapi uvicorn

# 2. Generate test audio
ffmpeg -f lavfi -i "sine=frequency=440:duration=30" \
  -ar 48000 -ac 2 -sample_fmt s24 -c:a flac test-loop.flac

# 3. Create streaming_server_loop.py (copy from above)
# 4. Create test_soco.py (copy from above)

# 5. Run (in terminal 1)
python streaming_server_loop.py

# 6. Run (in terminal 2)
python test_soco.py

# 7. Listen to Sonos Beam for 10+ minutes
# 8. Document results
```

---

## Part 9: Files Checklist

Ensure these files exist in `/home/a_manza/dev/turntabler/poc/soco-test/`:

- [ ] `streaming_server_loop.py` - Looping file server
- [ ] `streaming_server_generated.py` - Generated audio server (optional)
- [ ] `test_soco.py` - SoCo control script
- [ ] `test-loop.flac` - Test audio file (generated via ffmpeg)
- [ ] `requirements.txt` - Python dependencies
- [ ] `README.md` - Quick start guide
- [ ] `results.md` - Test results (fill after testing)

---

## Success Metrics

**Minimum viable POC:**
- Audio plays on Sonos ✓
- Runs for 10 minutes ✓
- Latency acceptable ✓

**Ideal POC:**
- All above ✓
- Runs for 30+ minutes without issues
- Can stop/restart cleanly
- Latency < 1 second
- Quality indistinguishable from lossless

---

## Decision Framework

After completing POC, use this to decide:

| Metric | SoCo | OwnTone | Winner |
|--------|------|---------|--------|
| Quality | Lossless FLAC | Lossy AAC-LC | SoCo |
| Streaming works? | Test result | Proven | ? |
| Complexity | Medium | High | SoCo |
| Proven for turntables | No | Yes | OwnTone |
| Latency | Test result | ~200-300ms | ? |

**If SoCo POC succeeds:** SoCo wins on quality + simplicity
**If SoCo POC fails:** OwnTone wins on proven reliability

---

## Timeline

**Total time:** 2-3 hours

- Setup: 15 min
- Coding: 30 min (copy-paste from this doc)
- Testing: 60-90 min (10+ min stream + troubleshooting)
- Documentation: 15 min (fill results template)
- Decision: 5 min

**End state:** Clear go/no-go decision on SoCo approach

---

## Next Steps After POC

**If SoCo succeeds:**
1. Update `/docs/implementation/tech-stack-decision.md`
2. Set up Python 3.13 + uv environment
3. Create `src/turntabler/backends/soco_backend.py`
4. Implement full streaming server
5. Add USB audio capture
6. Create CLI interface
7. Test with real turntable

**If SoCo fails:**
1. Document failure reasons in `results.md`
2. Update tech stack decision
3. Begin OwnTone installation
4. Follow `/docs/implementation/owntone-deep-dive.md`
5. Accept AAC-LC quality limitation

---

## Questions This POC Answers

- ✅ Can we stream continuous audio to Sonos via HTTP?
- ✅ Does `force_radio=True` work for indefinite streams?
- ✅ Is FLAC lossless quality delivered to Sonos?
- ✅ What is real-world latency?
- ✅ Is stability good enough for turntable use?
- ✅ Is this approach simpler than OwnTone?

**Ready to test!** 🚀
