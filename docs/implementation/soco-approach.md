# SoCo (Sonos Native Protocol) Approach

**Date:** 2025-11-14
**Status:** Recommended for evaluation

## Overview

SoCo is a Python library for controlling Sonos speakers using their native UPnP protocol. This approach streams audio via Sonos's native protocol (HTTP + FLAC) instead of AirPlay, delivering **true lossless quality**.

**Key advantage:** Sonos native protocol delivers **FLAC lossless**, while AirPlay delivers **AAC-LC lossy**.

---

## Why This Approach

### The Quality Problem with AirPlay

**Discovery:** AirPlay to Sonos delivers AAC-LC (lossy), not lossless ALAC

**Evidence:**
- Sonos Community forums confirm AirPlay is lossy to Sonos
- "For lossless audio on Sonos, you must do so from within the Sonos app"
- Native Sonos integration uses lossless codecs

### Solution: Use Sonos Native Protocol

**Architecture:**
```
Turntable (analog)
    ↓
USB Audio Interface (24-bit capture)
    ↓
Linux/Pi
  • Capture: arecord / ALSA
  • Encode: FLAC (real-time)
  • Serve: HTTP server
    ↓
Sonos Beam (HTTP fetch)
  • Native UPnP protocol
  • FLAC lossless playback
```

**Result:** True lossless audio path

---

## SoCo Library

### Overview

**Package:** `soco`
**PyPI:** https://pypi.org/project/soco/
**GitHub:** https://github.com/SoCo/SoCo (1,300+ stars)
**Documentation:** https://docs.python-soco.com/

**Maturity:**
- 10+ years active development
- Very mature, stable
- Excellent documentation
- Large community

**Python compatibility:**
- Requires Python 3.6+
- Compatible with Python 3.13
- Pure Python library

### Installation

```bash
pip install soco
```

### Basic Usage

```python
from soco import SoCo, discover

# Discover Sonos devices
devices = discover()
for device in devices:
    print(f"{device.player_name}: {device.ip_address}")

# Connect to specific device
sonos = SoCo('192.168.86.63')  # Sonos Beam IP

# Play audio from HTTP URI
sonos.play_uri(
    'http://192.168.86.100:8000/turntable.flac',
    title='Turntable',
    force_radio=True  # Continuous stream mode
)

# Control playback
sonos.pause()
sonos.play()
sonos.stop()

# Volume control
sonos.volume = 50
```

---

## HTTP Streaming Server

### Requirement

Sonos devices fetch audio from HTTP URIs. We must provide an HTTP server streaming our audio.

### Server Options

#### Option 1: Flask (Recommended for POC)

**Pros:**
- Simple, lightweight
- Easy to implement
- Good for testing

**Implementation:**
```python
from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route('/turntable.flac')
def stream_turntable():
    """Stream live audio from USB interface as FLAC"""
    def generate():
        # Start arecord process, encode to FLAC
        proc = subprocess.Popen([
            'arecord',
            '-D', 'hw:1,0',      # USB audio interface
            '-f', 'S24_LE',      # 24-bit (if supported)
            '-r', '48000',       # 48 kHz
            '-c', '2',           # Stereo
            '-t', 'flac',        # Output format: FLAC
        ], stdout=subprocess.PIPE)

        # Stream chunks to client
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk

    return Response(generate(), mimetype='audio/flac')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

**Usage:**
```bash
python http_server.py
# Access: http://localhost:8000/turntable.flac
```

#### Option 2: FastAPI (Modern Alternative)

**Pros:**
- Modern async framework
- Better performance
- Type hints support

**Implementation:**
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import subprocess

app = FastAPI()

@app.get('/turntable.flac')
async def stream_turntable():
    async def generate():
        proc = subprocess.Popen([
            'arecord', '-D', 'hw:1,0',
            '-f', 'S24_LE', '-r', '48000', '-c', '2',
            '-t', 'flac'
        ], stdout=subprocess.PIPE)

        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk

    return StreamingResponse(generate(), media_type='audio/flac')
```

**Run:**
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

#### Option 3: Icecast (Professional)

**Pros:**
- Designed for live streaming
- Handles multiple clients
- Industry standard
- Built-in buffering

**Cons:**
- More complex setup
- Overkill for single client
- Additional dependency

**Installation:**
```bash
sudo apt install icecast2
```

**Stream to Icecast:**
```bash
ffmpeg -f alsa -i hw:1,0 \
  -acodec flac \
  -ar 48000 \
  -ac 2 \
  -f ogg icecast://source:PASSWORD@localhost:8000/turntable
```

---

## Audio Capture & Encoding

### Capture Formats

**Supported by arecord:**
- S16_LE: 16-bit little-endian (standard)
- S24_LE: 24-bit little-endian (if interface supports)
- S32_LE: 32-bit little-endian

**Note:** Many USB interfaces claim 24-bit but use 24-bit-in-32-bit containers

### Real-Time FLAC Encoding

**Method 1: arecord built-in**
```bash
arecord -D hw:1,0 -f S24_LE -r 48000 -c 2 -t flac
```

**Pros:**
- Simple, one command
- FLAC encoding built into arecord
- Low CPU usage

**Method 2: FFmpeg**
```bash
ffmpeg -f alsa -i hw:1,0 \
  -acodec flac \
  -compression_level 5 \
  -ar 48000 \
  -ac 2 \
  -f flac -
```

**Pros:**
- More control over encoding
- Can adjust compression level (0-8)
- Better error handling

**Compression levels:**
- 0: Fastest, largest files
- 5: Balanced (recommended)
- 8: Slowest, smallest files

**Recommendation:** Level 5 for real-time streaming

---

## Complete Implementation Example

```python
# turntabler/backends/soco_backend.py

from soco import SoCo, discover
from flask import Flask, Response
import subprocess
import threading
from typing import Optional, List

class SoCoBackend:
    def __init__(self):
        self.sonos: Optional[SoCo] = None
        self.http_server = Flask(__name__)
        self.server_thread: Optional[threading.Thread] = None
        self.streaming_process: Optional[subprocess.Popen] = None

        # Register HTTP route
        @self.http_server.route('/turntable.flac')
        def stream():
            return self._stream_audio()

    def discover_devices(self) -> List[dict]:
        """Discover all Sonos devices on network"""
        devices = discover()
        return [{
            'name': device.player_name,
            'ip': device.ip_address,
            'model': device.get_speaker_info()['model_name']
        } for device in devices]

    def connect(self, device_name: str) -> bool:
        """Connect to specific Sonos device"""
        devices = discover()
        for device in devices:
            if device_name.lower() in device.player_name.lower():
                self.sonos = device
                return True
        return False

    def start_http_server(self, port: int = 8000):
        """Start HTTP server in background thread"""
        self.server_thread = threading.Thread(
            target=lambda: self.http_server.run(
                host='0.0.0.0',
                port=port,
                debug=False
            )
        )
        self.server_thread.daemon = True
        self.server_thread.start()

    def _stream_audio(self):
        """HTTP endpoint that streams FLAC audio"""
        def generate():
            self.streaming_process = subprocess.Popen([
                'arecord',
                '-D', 'hw:1,0',
                '-f', 'S24_LE',
                '-r', '48000',
                '-c', '2',
                '-t', 'flac'
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

            while True:
                chunk = self.streaming_process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

        return Response(generate(), mimetype='audio/flac')

    def stream_to_sonos(self, stream_url: str):
        """Tell Sonos to play our HTTP stream"""
        if not self.sonos:
            raise Exception("Not connected to Sonos device")

        self.sonos.play_uri(
            stream_url,
            title='Turntable',
            force_radio=True
        )

    def stop_streaming(self):
        """Stop Sonos playback and audio capture"""
        if self.sonos:
            self.sonos.stop()
        if self.streaming_process:
            self.streaming_process.terminate()

# Usage
backend = SoCoBackend()

# Discover Sonos
devices = backend.discover_devices()
print(f"Found: {devices}")

# Connect to Beam
backend.connect('Beam')

# Start HTTP server
backend.start_http_server(port=8000)

# Stream to Sonos
import socket
my_ip = socket.gethostbyname(socket.gethostname())
backend.stream_to_sonos(f'http://{my_ip}:8000/turntable.flac')
```

---

## Pros & Cons

### Pros

✅ **True lossless** - FLAC to Sonos, not AAC-LC
✅ **Native Python** - SoCo library mature, well-documented
✅ **Simpler architecture** - No full server like OwnTone
✅ **Direct control** - UPnP protocol, no JSON API wrapper
✅ **24-bit potential** - Can stream 24-bit FLAC (may be truncated by Sonos)
✅ **Pi-portable** - Same code runs on Ubuntu and Pi
✅ **Educational** - Learn HTTP streaming, UPnP protocol

### Cons

❌ **Must implement HTTP server** - Extra complexity vs turnkey
❌ **Real-time encoding** - Must encode FLAC fast enough
❌ **Network requirement** - Sonos must reach HTTP server
❌ **No auto-detection** - Must manually start streaming
❌ **Unknown latency** - Need testing (could be higher than AirPlay)
❌ **Less proven** - Not purpose-built like OwnTone

---

## Testing Checklist

### Phase 1: SoCo Basics (30 min)
- [ ] Install SoCo: `pip install soco`
- [ ] Test device discovery
- [ ] Connect to Sonos Beam
- [ ] Test play_uri with internet radio stream
- [ ] Verify basic control works

### Phase 2: HTTP Server (1 hour)
- [ ] Implement Flask server
- [ ] Serve static FLAC file
- [ ] Test Sonos can play from HTTP server
- [ ] Verify FLAC playback quality

### Phase 3: Real-Time Streaming (2 hours)
- [ ] Implement real-time audio capture
- [ ] Stream via HTTP to Sonos
- [ ] Test with USB audio interface
- [ ] Measure latency (target < 1 second)

### Phase 4: Quality Validation (1 hour)
- [ ] Use Wireshark to verify FLAC codec
- [ ] Check if 24-bit preserved or truncated
- [ ] A/B test vs direct Sonos app playback
- [ ] Compare to AirPlay quality

### Phase 5: Reliability Testing (1 hour)
- [ ] Long-duration streaming (1+ hour)
- [ ] Network interruption recovery
- [ ] Buffer underrun handling
- [ ] CPU usage monitoring

---

## Open Questions (Need Testing)

### 1. Latency

**Question:** What is real-time HTTP streaming latency?

**Acceptable:** < 1 second for turntable use case

**Test method:**
- Play transient sound (click, drumbeat)
- Measure time from source to Sonos output
- Compare to AirPlay latency (~200-300ms)

### 2. Quality

**Question:** Does Sonos actually receive 24-bit FLAC, or truncate to 16-bit?

**Test method:**
- Stream 24-bit/48kHz FLAC
- Use Wireshark to inspect HTTP stream
- Check Sonos network activity/bandwidth
- Listen for quality differences

### 3. Stability

**Question:** How stable is real-time HTTP streaming?

**Test method:**
- Stream for multiple hours
- Monitor for dropouts
- Test network congestion scenarios
- Verify CPU usage sustainable

### 4. Comparison to AirPlay

**Question:** Is native Sonos meaningfully better than AirPlay?

**Test method:**
- A/B listening test
- Same source, both protocols
- Blind test if possible
- Document subjective findings

---

## Fallback Strategy

**If SoCo approach proves problematic:**

**Issues that would trigger fallback:**
- Latency > 2 seconds (unacceptable)
- Frequent dropouts/instability
- Real-time FLAC encoding CPU too high
- Implementation complexity too great

**Fallback:** OwnTone (AirPlay)
- Accept AAC-LC lossy quality
- Benefit from purpose-built solution
- Proven stability and maturity

---

## Recommendation

**Try SoCo first** because:
1. Only way to get lossless to Sonos
2. Simpler architecture than full server
3. Native Python integration
4. Worth testing before accepting lossy AirPlay

**Time investment:** 4-6 hours to validate approach

**If successful:** Proceed with SoCo implementation

**If problematic:** Fall back to OwnTone with eyes open about quality limitation

---

## References

- [SoCo Documentation](https://docs.python-soco.com/)
- [SoCo GitHub](https://github.com/SoCo/SoCo)
- [Sonos Supported Formats](https://support.sonos.com/en-us/article/supported-audio-formats-for-sonos-music-library)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Sonos UPnP (unofficial)](https://en.community.sonos.com/advanced-setups-229000/sonos-api-6858805)
