# OwnTone Deep-Dive Research Results

**Date:** 2025-11-14
**Status:** Complete

## Executive Summary

OwnTone is a mature, purpose-built solution for streaming analog audio (turntables) to AirPlay devices. However, **critical discovery**: AirPlay to Sonos delivers **AAC-LC lossy codec**, not lossless, defeating our audio quality goals.

**Recommendation:** Consider Sonos native protocol instead (see sonos-native-vs-airplay.md)

---

## OwnTone Overview

**Official name:** OwnTone (formerly forked-daapd)
**Website:** https://owntone.github.io/owntone-server/
**GitHub:** https://github.com/owntone/owntone-server
**Latest version:** 29.0 (September 2025)

### What It Is

Full-featured music server with support for:
- AirPlay 1 and 2 (sender)
- Chromecast
- DAAP (iTunes protocol)
- MPD (Music Player Daemon)
- Web UI for control
- Named pipe input (for live audio)

### Designed Use Case

Exactly our use case! Official wiki page: ["Making an Analog In to Airplay RPi Transmitter"](https://github.com/owntone/owntone-server/wiki/Making-an-Analog-In-to-Airplay-RPi-Transmitter)

---

## Audio Quality Specifications

### Input: Pipe Format (VERIFIED FROM SOURCE CODE)

**Source:** `src/inputs/pipe.c`

**Supported sample rates:**
- 44.1 kHz
- 48 kHz
- 88.2 kHz
- 96 kHz

**Supported bit depths:**
- **16-bit** (PCM16)
- **32-bit** (PCM32)
- **NOT 24-bit** (hardcoded restriction in source)

**Channels:**
- Stereo (2-channel) only
- No mono or surround support

**Format:** Raw PCM audio via named pipes (FIFO)

**Critical limitation:** Cannot accept 24-bit audio directly. Must use 16-bit or 32-bit.

### Output: AirPlay Quality

**AirPlay 2 protocol capabilities:**
- ALAC codec (lossless)
- Up to 24-bit/48kHz theoretically

**OwnTone capabilities:**
- Version 27+ supports "native sample rate/bit rate"
- Can send ALAC encoded streams
- Multi-room synchronization

**HOWEVER:** When streaming to Sonos via AirPlay:
- Sonos receives **AAC-LC (lossy)**
- Not ALAC lossless
- This is an AirPlay→Sonos limitation, not OwnTone

**Result:** End-to-end quality is 16-bit AAC-LC (lossy)

---

## Installation

### Ubuntu 22.04

**Option 1: Third-party repository (Recommended)**

```bash
# Add repository
sudo curl https://git.sudo.is/api/packages/ben/debian/repository.key \
  -o /etc/apt/keyrings/git.sudo.is-ben.asc

echo "deb [signed-by=/etc/apt/keyrings/git.sudo.is-ben.asc] \
  https://git.sudo.is/api/packages/ben/debian jammy main" | \
  sudo tee -a /etc/apt/sources.list.d/git.sudo.is-ben.list

# Install
sudo apt update
sudo apt install owntone-server
```

**Option 2: Build from source**

- Follow: https://owntone.github.io/owntone-server/building/
- Dependencies: Many (libavcodec, libavformat, libasound2, etc.)
- Time estimate: 2-3 hours
- Complexity: High

### Raspberry Pi OS (Bookworm)

**Official OwnTone APT repository:**

```bash
# Add repo from https://github.com/owntone/owntone-apt/
sudo apt update
sudo apt install owntone
```

**Status:** Available, users report successful installation

**Known issues:**
- Some dependency conflicts with libavfilter/libavformat reported
- Generally solvable

---

## Configuration

### Location

`/etc/owntone.conf`

### Key Settings

**General section:**
```conf
general {
    uid = "owntone"
    admin_password = "your_password"
    websocket_port = 3688
    trusted_networks = { "192.168.1.0/24" }
}
```

**Library section:**
```conf
library {
    name = "Turntable Stream"
    directories = { "/home/user/music" }
    pipe_autostart = true  # Auto-detect pipe audio
}
```

**Pipe input quality:**
```conf
# In config file, set:
pipe_sample_rate = 48000  # 44100, 48000, 88200, or 96000
pipe_bits_per_sample = 16 # 16 or 32 only (NOT 24)
```

**AirPlay settings:**
```conf
airplay {
    enabled = true
    # No explicit 24-bit config found in template
}
```

---

## Turntable Setup Workflow

### Official Guide Summary

From: https://github.com/owntone/owntone-server/wiki/Making-an-Analog-In-to-Airplay-RPi-Transmitter

**Step 1: Create named pipe**
```bash
mkfifo -m 666 /home/pi/music/TURNTABLE
```

**Step 2: Capture USB audio to pipe**
```bash
# Basic (16-bit/44.1kHz - CD quality)
arecord -D hw:1,0 -f S16_LE -c 2 -r 44100 -t raw > /home/pi/music/TURNTABLE

# Higher quality (16-bit/48kHz)
arecord -D hw:1,0 -f S16_LE -c 2 -r 48000 -t raw > /home/pi/music/TURNTABLE

# 32-bit (if interface supports, downsampled from 24-bit)
arecord -D hw:1,0 -f S32_LE -c 2 -r 48000 -t raw > /home/pi/music/TURNTABLE
```

**Step 3: OwnTone auto-detection**
- OwnTone monitors music directory
- Detects audio being written to pipe
- Automatically starts streaming to enabled AirPlay devices

**Step 4: Advanced - Auto start/stop with cpiped**

Tool: https://github.com/b-fitzpatrick/cpiped

- Detects when audio is present (above silence threshold)
- Automatically starts `arecord` when turntable playing
- Stops when silence detected
- Prevents constant streaming when turntable off

---

## JSON API Integration

### API Documentation

**URL:** https://owntone.github.io/owntone-server/json-api/
**Protocol:** HTTP/JSON
**Port:** 3689 (default)

### Key Endpoints

**Device/Output Control:**
```http
GET /api/outputs
# Returns list of AirPlay devices

PUT /api/outputs/set
Body: {"outputs": ["sonos_beam_id"]}
# Enable specific outputs

PUT /api/outputs/{id}
Body: {"selected": true, "volume": 75}
# Control individual output
```

**Playback Control:**
```http
GET /api/player
# Get player status

PUT /api/player/play
PUT /api/player/pause
PUT /api/player/stop

PUT /api/player/volume?volume=50
```

**Queue Management:**
```http
GET /api/queue
# List current queue

POST /api/queue/items/add?uris=library:track:123
```

### Python Integration

**No official Python library exists**

**Must implement HTTP client:**
```python
import requests

class OwnToneAPI:
    def __init__(self, base_url='http://localhost:3689'):
        self.base_url = base_url

    def get_outputs(self):
        r = requests.get(f'{self.base_url}/api/outputs')
        return r.json()['outputs']

    def enable_device(self, device_name):
        outputs = self.get_outputs()
        for output in outputs:
            if device_name.lower() in output['name'].lower():
                requests.put(
                    f"{self.base_url}/api/outputs/{output['id']}",
                    json={'selected': True}
                )
                return True
        return False
```

**Complexity:** Low-Medium (straightforward HTTP/JSON)
**Time estimate:** 1-2 hours to build wrapper

---

## Sonos Compatibility

### Tested Configurations

**From GitHub issues:**
- Issue #557: Sonos Beam with AirPlay 2 reported working
- Issue #613: Volume control from Sonos buttons may not work
- Issue #1016: PIN pairing issues with some Sonos devices

### Network Requirements

**Firewall:**
- May need to open UDP ports 6001-6002 for some devices
- Both OwnTone and Sonos must be able to reach each other
- No NAT between devices

**Recommendation:** Same subnet, allow traffic between devices

### Known Issues

**Volume control:**
- Sonos device volume buttons may not control OwnTone volume
- Use OwnTone web UI or API for volume control

**Pairing:**
- Some Sonos devices may request PIN
- Sonos doesn't provide PINs
- Workaround: Configure pairing settings in OwnTone

---

## Performance

### Resource Usage

**From Raspberry Pi user reports:**
- CPU: < 10% on Raspberry Pi 4 (idle)
- Memory: ~50-100 MB RAM
- I/O: Minimal except during library scans
- Network: ~1 Mbps for lossless streaming

**Raspberry Pi 5:** Should run very well (more powerful than Pi 4)

### Latency

**Expected:** 200-300ms (typical for AirPlay)
**Acceptable for turntable:** Yes (not interactive playback)

---

## Pros & Cons Summary

### Pros

✅ **Purpose-built** for exactly our use case (turntable → AirPlay)
✅ **Mature** - 10+ years development, stable
✅ **Active development** - v29.0 released September 2025
✅ **Well-documented** - Official wiki page for turntable setup
✅ **Auto-detection** - Pipe input automatically starts playback
✅ **Multi-room** - AirPlay 2 multi-speaker support
✅ **Web UI** - Easy control and monitoring
✅ **Pi-ready** - Proven on Raspberry Pi
✅ **Community support** - Active users, responsive maintainer

### Cons

❌ **Critical: AAC-LC to Sonos** - Not lossless!
❌ **Heavyweight** - Full server (overkill for simple use case)
❌ **16-bit max input** - Cannot accept 24-bit pipes (only 16 or 32-bit)
❌ **No official Python library** - Must write JSON API wrapper
❌ **Complex setup** - Installation not in official repos
❌ **Configuration complexity** - Many options, steep learning curve

---

## Decision Factors

### When to Choose OwnTone

**Choose OwnTone if:**
- AirPlay 2 multi-room is important
- You want turnkey solution despite complexity
- You can accept AAC-LC quality to Sonos
- You value maturity over simplicity

### When NOT to Choose OwnTone

**Avoid OwnTone if:**
- **Lossless quality to Sonos is critical** (use Sonos native instead)
- You want simpler architecture
- You prefer pure Python solutions
- Installation complexity is a concern

---

## Alternative: SoCo (Sonos Native)

**See:** `docs/research/sonos-native-vs-airplay.md`

**Key difference:**
- SoCo → Sonos native protocol → **FLAC lossless**
- OwnTone → AirPlay → Sonos → **AAC-LC lossy**

**Recommendation:** Evaluate SoCo first for better quality

---

## Testing Checklist (If Using OwnTone)

### Phase 1: Basic Setup
- [ ] Install OwnTone on Ubuntu
- [ ] Configure admin password, trusted networks
- [ ] Access web UI (http://localhost:3689)
- [ ] Test with MP3/FLAC file playback

### Phase 2: Sonos Connection
- [ ] Verify Sonos Beam appears in outputs
- [ ] Enable Sonos output
- [ ] Test audio playback to Sonos
- [ ] Measure latency (acceptable < 500ms)

### Phase 3: Pipe Input
- [ ] Create named pipe in music directory
- [ ] Test with `arecord` piping audio
- [ ] Verify auto-detection works
- [ ] Test audio quality (subjective)

### Phase 4: Quality Validation
- [ ] Use Wireshark to capture AirPlay traffic
- [ ] Verify codec (expect AAC-LC, not ALAC)
- [ ] A/B test vs direct Sonos app playback
- [ ] Document actual quality received

### Phase 5: Python Integration
- [ ] Implement JSON API wrapper
- [ ] Test device discovery via API
- [ ] Test output enable/disable
- [ ] Test playback control

---

## Conclusion

**OwnTone verdict:** Excellent solution for AirPlay streaming, but **not optimal for TurnTabler** due to AAC-LC lossy quality when streaming to Sonos.

**Recommendation:** Explore SoCo (Sonos native protocol) first for true lossless quality. Fall back to OwnTone only if native streaming proves problematic.

---

## References

- [OwnTone Official Docs](https://owntone.github.io/owntone-server/)
- [GitHub Repository](https://github.com/owntone/owntone-server)
- [Turntable Wiki](https://github.com/owntone/owntone-server/wiki/Making-an-Analog-In-to-Airplay-RPi-Transmitter)
- [JSON API Docs](https://owntone.github.io/owntone-server/json-api/)
- [Installation Guide](https://owntone.github.io/owntone-server/installation/)
- [Configuration Reference](https://raw.githubusercontent.com/owntone/owntone-server/refs/heads/master/owntone.conf.in)
