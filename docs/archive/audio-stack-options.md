# Linux Audio Stack Options for AirPlay Sending

## Overview
This document evaluates different approaches to send audio from Linux to AirPlay devices (Sonos Beam) with lossless quality.

## Option 1: VLC

### Description
VLC media player has built-in RAOP (AirPlay) streaming output capability.

### How It Works
```bash
# Basic syntax
cvlc INPUT --sout '#raop{host=DEVICE_IP}' --no-sout-video

# With ALAC transcode (explicit lossless)
cvlc audio.flac --sout '#transcode{acodec=alac,ab=256,channels=2,samplerate=48000}:raop{host=192.168.1.100}' --no-sout-video
```

### Python Integration Options

**A. Subprocess (Simplest)**
```python
import subprocess

subprocess.run([
    'cvlc', 'audio.flac',
    '--sout', '#raop{host=192.168.1.100}',
    '--no-sout-video',
    '--intf', 'dummy'  # No GUI
])
```

**B. python-vlc bindings (More Control)**
```python
import vlc

instance = vlc.Instance('--sout=#raop{host=192.168.1.100}')
player = instance.media_player_new()
media = instance.media_new('audio.flac')
player.set_media(media)
player.play()
```

### Pros
✅ Proven to work (documented in research)
✅ Simple command-line usage
✅ ALAC support confirmed
✅ Available on both Ubuntu and Raspberry Pi
✅ No complex configuration needed
✅ Handles many input formats automatically

### Cons
❌ External binary dependency (not pure Python)
❌ Subprocess control has limited feedback
❌ Error handling can be tricky
❌ Less fine-grained control over streaming parameters

### Quality
- **Codec:** ALAC (lossless)
- **Max bit depth:** 24-bit
- **Max sample rate:** 48 kHz (limited by AirPlay 2)
- **Latency:** ~200-300ms (typical for AirPlay)

### Installation
```bash
# Ubuntu/Debian
sudo apt install vlc vlc-plugin-base

# Raspberry Pi OS
sudo apt install vlc
```

### Verdict
**Excellent choice for initial POC.** Simple, proven, easy Python integration.

---

## Option 2: GStreamer

### Description
GStreamer is a professional-grade multimedia framework with extensive plugin ecosystem, including RAOP output.

### How It Works
```bash
# Basic pipeline
gst-launch-1.0 \
  filesrc location=audio.flac ! \
  decodebin ! \
  audioconvert ! \
  audioresample ! \
  raopsink host=192.168.1.100
```

### Python Integration
```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

pipeline = Gst.parse_launch(
    'filesrc location=audio.flac ! '
    'decodebin ! audioconvert ! audioresample ! '
    'raopsink host=192.168.1.100'
)

pipeline.set_state(Gst.State.PLAYING)
```

### Pros
✅ Professional-grade audio processing
✅ Excellent format support
✅ Fine-grained control over pipeline
✅ Python bindings are mature (PyGObject)
✅ Can handle live input (future USB audio interface)
✅ Widely used on Raspberry Pi
✅ Better error handling and state management

### Cons
❌ More complex than VLC
❌ Steeper learning curve
❌ Requires understanding pipeline architecture
❌ More dependencies (gi, Gst plugins)

### Quality
- **Codec:** ALAC (via raopsink)
- **Max bit depth:** 24-bit
- **Max sample rate:** 192 kHz (resampled to 48 kHz for AirPlay)
- **Latency:** ~200-300ms

### Installation
```bash
# Ubuntu/Debian
sudo apt install \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  python3-gi \
  gir1.2-gstreamer-1.0

# Check for raopsink availability
gst-inspect-1.0 raopsink
```

### Verdict
**Best for production system.** More complex initially, but superior flexibility and control. Ideal for future USB input integration.

---

## Option 3: PipeWire / PulseAudio RAOP Module

### Description
System audio server approach. Creates virtual audio sinks that route to AirPlay devices.

### How It Works

**PipeWire (Modern):**
```bash
# Load RAOP discovery module
pactl load-module module-raop-discover

# List available sinks (should show Sonos)
pactl list sinks short

# Set Sonos as default output
pactl set-default-sink <sonos_sink_name>
```

**PulseAudio (Older):**
```bash
# Install RAOP module
sudo apt install pulseaudio-module-raop

# Load module
pactl load-module module-raop-discover

# Same usage as PipeWire
```

### Python Integration
```python
import pulsectl

with pulsectl.Pulse('turntabler') as pulse:
    # Load RAOP module
    pulse.module_load('module-raop-discover')

    # Find Sonos sink
    sinks = pulse.sink_list()
    sonos_sink = next(s for s in sinks if 'Sonos' in s.description)

    # Route audio source to sink
    # (requires more code for file playback)
```

### Pros
✅ System-level integration
✅ Can route ANY audio to Sonos (files, apps, system sounds)
✅ Good for "always-on" streaming use case
✅ Auto-discovery of AirPlay devices
✅ Already installed on most Linux systems

### Cons
❌ System dependency (must configure audio server)
❌ Less portable (Pi might use different audio system)
❌ More complex to route individual files
❌ Harder to control programmatically vs subprocess
❌ Requires audio server restart for some changes

### Quality
- **Codec:** ALAC
- **Max bit depth:** 24-bit
- **Max sample rate:** 48 kHz
- **Latency:** ~200-400ms

### Installation
```bash
# Check current audio server
pactl info  # or pw-cli info

# Install RAOP module (if not present)
sudo apt install pipewire-module-raop  # PipeWire
# OR
sudo apt install pulseaudio-module-raop  # PulseAudio
```

### Verdict
**Good for system-wide audio routing**, but overkill for our specific use case (streaming one source). Better suited for Phase 2 (system audio streaming).

---

## Option 4: FFmpeg

### Description
FFmpeg is a comprehensive audio/video processing tool with extensive codec support.

### How It Works
```bash
# Basic RAOP output (need to verify exact syntax)
ffmpeg -i audio.flac \
  -c:a alac \
  -f raop \
  rtsp://192.168.1.100:7000
```

**Note:** RAOP output support in FFmpeg needs verification. It has excellent ALAC encoding but RAOP network output may require additional setup.

### Python Integration
```python
import subprocess

subprocess.run([
    'ffmpeg',
    '-i', 'audio.flac',
    '-c:a', 'alac',
    '-f', 'raop',
    'rtsp://192.168.1.100:7000'
])
```

### Pros
✅ Excellent codec support
✅ Powerful audio processing capabilities
✅ Can handle format conversion seamlessly
✅ Available everywhere
✅ Well-documented

### Cons
❌ RAOP output support unclear (needs testing)
❌ May require additional tools (like avahi for discovery)
❌ Subprocess-based control only
❌ Complex command-line syntax

### Quality
- **Codec:** ALAC (excellent encoder)
- **Max bit depth:** 32-bit (but limited by AirPlay)
- **Max sample rate:** 384 kHz (resampled for AirPlay)

### Installation
```bash
sudo apt install ffmpeg
```

### Verdict
**Needs testing.** If RAOP output works, could be good option. Fallback: Use FFmpeg for format conversion, then pipe to VLC/GStreamer.

---

## Comparison Matrix

| Feature | VLC | GStreamer | PipeWire/PA | FFmpeg |
|---------|-----|-----------|-------------|--------|
| **Ease of use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Python control** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Flexibility** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Pi portability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Documentation** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **RAOP proven** | ✅ Yes | ✅ Yes | ✅ Yes | ❓ Needs test |
| **Live input ready** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Recommendation for TurnTabler

### Phase 1 POC: VLC
**Rationale:**
- Fastest path to working prototype
- Proven in research documentation
- Simple Python subprocess integration
- Easy to test and validate quality

**Implementation approach:**
```python
# src/turntabler/backends/vlc.py
class VLCStreamer:
    def stream_file(self, file_path, device_ip):
        subprocess.run([
            'cvlc', file_path,
            '--sout', f'#raop{{host={device_ip}}}',
            '--no-sout-video',
            '--intf', 'dummy'
        ])
```

### Future (Phase 3+): GStreamer
**When to switch:**
- When adding USB audio interface input
- If need more control over audio processing
- For production deployment on Pi

**Why better for live input:**
```python
# Can create pipeline like:
# alsasrc (USB input) → audioconvert → raopsink (Sonos)
# Much cleaner than VLC for live streams
```

### System Audio (Phase 2): PipeWire RAOP
**Use case:**
- Route ALL computer audio to Sonos
- Background music, browser audio, etc.
- Complementary to file/USB streaming

---

## Testing Plan

### VLC Testing (First)
1. Install VLC
2. Test command-line RAOP streaming to Sonos
3. Verify ALAC codec in use
4. Measure latency and quality
5. Implement Python subprocess control
6. Create backend abstraction

### GStreamer Testing (Secondary)
1. Install GStreamer + plugins
2. Test raopsink availability and functionality
3. Compare quality/latency to VLC
4. Prototype Python bindings usage
5. Document for future migration

### PipeWire Testing (Optional)
1. Check if RAOP module available
2. Test system audio routing
3. Document for Phase 2 system audio feature

---

## Next Steps

1. **Implement VLC backend** (src/turntabler/backends/vlc.py)
2. **Create backend abstraction** (src/turntabler/streaming.py)
3. **Test quality with real audio files**
4. **Document results** (docs/implementation/tech-stack-decision.md)
5. **Leave door open for GStreamer** (design allows swapping backends)
