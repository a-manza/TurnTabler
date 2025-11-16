# Tech Stack Decision for TurnTabler Phase 1

**Date:** 2025-11-14 (Updated)
**Status:** Complete - Recommendation Ready

## Environment

**System:** Ubuntu 22.04 (Linux 6.8.0-87-generic)
**Python:** 3.8.3 (target: 3.13 for project)
**Audio Server:** PipeWire 0.3.48 (with PulseAudio compatibility)
**Network Discovery:** Avahi daemon active

**Sonos Beam Discovered:**
- **Hostname:** Sonos-542A1BDF8748.local
- **IP Address:** 192.168.86.63
- **Service:** _raop._tcp (AirPlay)
- **Transport:** UDP (AirPlay 2)
- **Model:** Beam (am=Beam in TXT record)
- **Firmware:** p20.91.0-70070

## Options Under Evaluation

### Option A: VLC

**Current Status:** Installed via Snap (v3.0.20)

**Pros:**
- Already installed
- Documented to work in research
- Simple subprocess control
- Handles multiple audio formats

**Cons:**
- Snap version may have sandboxing issues
- RAOP plugin availability unclear in snap
- May need apt install instead

**Testing Plan:**
1. Check RAOP plugin availability
2. If not available in snap, install via apt
3. Test basic RAOP streaming to 192.168.86.63
4. Verify ALAC codec usage
5. Measure latency and quality

**Commands to test:**
```bash
# Install apt version if needed
sudo apt install vlc vlc-plugin-base vlc-plugin-access-extra

# Test streaming
cvlc /path/to/audio.wav \\
  --sout '#raop{host=192.168.86.63}' \\
  --no-sout-video \\
  --intf dummy
```

---

### Option B: GStreamer

**Current Status:** Need to check installation

**Testing Plan:**
1. Install GStreamer + plugins
2. Check for raopsink plugin
3. Test pipeline to Sonos
4. Evaluate Python bindings

**Commands to test:**
```bash
# Install
sudo apt install \\
  gstreamer1.0-tools \\
  gstreamer1.0-plugins-base \\
  gstreamer1.0-plugins-good \\
  gstreamer1.0-plugins-bad \\
  python3-gi \\
  gir1.2-gstreamer-1.0

# Check for raopsink
gst-inspect-1.0 raopsink

# Test pipeline
gst-launch-1.0 \\
  filesrc location=test.wav ! \\
  wavparse ! \\
  audioconvert ! \\
  audioresample ! \\
  raopsink host=192.168.86.63
```

---

### Option C: PipeWire RAOP Module

**Current Status:** PipeWire 0.3.48 installed

**Testing Plan:**
1. Check if RAOP module available
2. Test loading module and device discovery
3. Evaluate programmatic control via pulsectl

**Commands to test:**
```bash
# Check for RAOP module
pactl list modules short | grep raop

# Load RAOP discovery
pactl load-module module-raop-discover

# List sinks (should show Sonos)
pactl list sinks short
```

---

## Testing Methodology

### Quality Metrics to Measure

1. **Codec Verification**
   - Confirm ALAC encoding (not AAC/MP3)
   - Check via Wireshark or tool logs

2. **Latency**
   - Measure time from command to audio output
   - Target: < 500ms acceptable

3. **Audio Quality**
   - Subjective listening test
   - No audible artifacts or compression

4. **Reliability**
   - Connection stability
   - Error handling

5. **Python Integration**
   - Ease of subprocess control
   - Ability to get status/feedback

### Test Audio Files Needed

Create test files with different qualities:
- 16-bit/44.1kHz WAV (CD quality)
- 24-bit/48kHz FLAC (target quality)
- MP3 (to verify transcoding to lossless)

---

## Decision Criteria

| Criterion | Weight | Notes |
|-----------|--------|-------|
| Audio Quality | CRITICAL | Must be lossless (ALAC) |
| Ease of Python Control | HIGH | Subprocess vs bindings |
| Reliability | HIGH | Stable streaming, error handling |
| Pi Portability | HIGH | Must work on Raspberry Pi OS |
| Setup Complexity | MEDIUM | Prefer simpler for POC |
| Long-term Flexibility | MEDIUM | Can we swap later? |

---

## Test Results

### VLC Testing

**Installation:**
- [ ] Snap version tested
- [ ] Apt version installed (if needed)
- [ ] RAOP plugin confirmed available

**Streaming Test:**
- [ ] Successfully connected to Sonos Beam
- [ ] Audio played without errors
- [ ] ALAC codec confirmed
- [ ] Latency measured: ___ ms
- [ ] Quality assessment: ___

**Python Control:**
- [ ] Subprocess control tested
- [ ] python-vlc bindings tested (optional)
- [ ] Error handling verified

**Issues/Notes:**
- (To be filled during testing)

---

### GStreamer Testing

**Installation:**
- [ ] GStreamer installed
- [ ] raopsink plugin available
- [ ] Python bindings working

**Streaming Test:**
- [ ] Pipeline successfully created
- [ ] Connected to Sonos Beam
- [ ] Audio played without errors
- [ ] ALAC codec confirmed
- [ ] Latency measured: ___ ms
- [ ] Quality assessment: ___

**Python Control:**
- [ ] PyGObject bindings tested
- [ ] Pipeline control demonstrated
- [ ] Error handling verified

**Issues/Notes:**
- (To be filled during testing)

---

### PipeWire Testing

**Setup:**
- [ ] RAOP module available
- [ ] Module loaded successfully
- [ ] Sonos Beam appeared as sink

**Streaming Test:**
- [ ] Audio routed to Sonos sink
- [ ] ALAC codec confirmed
- [ ] Latency measured: ___ ms
- [ ] Quality assessment: ___

**Python Control:**
- [ ] pulsectl tested
- [ ] Sink control demonstrated

**Issues/Notes:**
- (To be filled during testing)

---

## CRITICAL DISCOVERY: AirPlay Quality Issue

**Date:** 2025-11-14

### Research Finding

AirPlay to Sonos delivers **AAC-LC (lossy codec)**, NOT lossless ALAC, even though:
- AirPlay 2 protocol supports lossless
- Devices support 24-bit/48kHz
- OwnTone can send ALAC

**Source:** Multiple Sonos Community posts confirm this

**Impact:** Any AirPlay-based solution (VLC, GStreamer, PipeWire RAOP, OwnTone) will deliver **lossy audio** to Sonos, defeating our lossless goal.

### Solution: Sonos Native Protocol

Sonos's native UPnP protocol delivers **FLAC lossless** when streaming via HTTP.

**See detailed docs:**
- `/docs/research/sonos-native-vs-airplay.md`
- `/docs/implementation/owntone-deep-dive.md`
- `/docs/implementation/soco-approach.md`

---

## Final Recommendations

### PRIMARY: SoCo (Sonos Native Protocol)

**Approach:** Stream FLAC via HTTP, use SoCo (Python library) to control Sonos via UPnP

**Why:**
- ✅ **True lossless** - FLAC to Sonos, not AAC-LC
- ✅ **Native Python** - SoCo library mature, excellent docs
- ✅ **Simpler** - No full server needed
- ✅ **24-bit potential** - Can stream 24-bit FLAC
- ✅ **Pi-portable** - Same code on Ubuntu & Pi

**Implementation:**
1. HTTP server (Flask/FastAPI) streaming FLAC
2. SoCo library to control Sonos playback
3. Real-time audio capture → FLAC encoding → HTTP stream

**Status:** Needs validation testing

**See:** `/docs/implementation/soco-approach.md`

**Confidence:** 8/10 (pending real-time streaming validation)

---

### SECONDARY: OwnTone (AirPlay 2)

**Approach:** Purpose-built server for turntable → AirPlay streaming

**Why:**
- ✅ Purpose-built for exactly our use case
- ✅ Mature, proven on Raspberry Pi + turntables
- ✅ Auto-detection of pipe input
- ✅ Multi-room AirPlay 2

**Critical Limitation:**
- ❌ **Delivers AAC-LC lossy** to Sonos (not lossless)
- ❌ 16-bit maximum (pipe input limitation)
- ❌ Heavyweight (full server)
- ❌ Complex installation

**When to use:** If SoCo approach proves too problematic (latency, stability issues)

**See:** `/docs/implementation/owntone-deep-dive.md`

**Confidence:** 9/10 (proven, but accept lossy quality)

---

## Decision Matrix

| Criterion | SoCo (Native) | OwnTone (AirPlay) | Weight |
|-----------|---------------|-------------------|--------|
| **Audio Quality** | 🟢 FLAC lossless | 🔴 AAC-LC lossy | CRITICAL |
| **Bit Depth** | 24-bit possible | 16-bit max | HIGH |
| **Python Integration** | 🟢 Native (SoCo) | 🟡 JSON API | HIGH |
| **Setup Complexity** | Medium | High | MEDIUM |
| **Purpose-Built** | No | 🟢 Yes | MEDIUM |
| **Pi Portability** | ✅ Yes | ✅ Yes | HIGH |
| **Maturity** | Very mature | Very mature | HIGH |
| **Installation** | `pip install` | Build/PPA | MEDIUM |
| **Proven for Turntables** | Unknown | 🟢 Yes | HIGH |

**Winner:** SoCo for quality, OwnTone for proven solution

---

## Recommendation

**Phase 1A: Validate SoCo Approach (4-6 hours)**

Test if Sonos native protocol works for real-time streaming:

1. Install SoCo library
2. Build simple HTTP streaming server (Flask)
3. Test real-time FLAC encoding
4. Measure latency and quality
5. Validate stability

**If successful:** Proceed with SoCo implementation
- Better quality (lossless FLAC)
- Simpler architecture
- Native Python

**If problematic:** Fall back to OwnTone
- Accept AAC-LC quality limitation
- Benefit from turnkey solution
- Proven with turntables

**Time to decision:** 1 day of testing

---

## Implementation Plan (After Decision)

### For VLC Backend:
```python
# src/turntabler/backends/vlc.py

import subprocess
from pathlib import Path

class VLCStreamer:
    def stream_file(self, file_path: Path, device_ip: str):
        cmd = [
            'cvlc', str(file_path),
            '--sout', f'#raop{{host={device_ip}}}',
            '--no-sout-video',
            '--intf', 'dummy'
        ]
        subprocess.run(cmd)
```

### For GStreamer Backend:
```python
# src/turntabler/backends/gstreamer.py

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class GStreamerStreamer:
    def __init__(self):
        Gst.init(None)

    def stream_file(self, file_path: Path, device_ip: str):
        pipeline_str = (
            f'filesrc location={file_path} ! '
            'decodebin ! audioconvert ! audioresample ! '
            f'raopsink host={device_ip}'
        )
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.pipeline.set_state(Gst.State.PLAYING)
```

---

## Next Steps

1. [ ] Install any missing packages
2. [ ] Create test audio files
3. [ ] Run VLC tests
4. [ ] Run GStreamer tests (if time permits)
5. [ ] Document results in this file
6. [ ] Make final recommendation
7. [ ] Update claude.md with decision
8. [ ] Proceed to Task 2 (Environment Setup)

---

## References

- [VLC RAOP Documentation](https://wiki.videolan.org/Documentation:Streaming_HowTo/)
- [GStreamer raopsink](https://gstreamer.freedesktop.org/documentation/raop/raopsink.html)
- [PipeWire RAOP Module](https://docs.pipewire.org/page_module_raop_sink.html)
- Our research: `/docs/linux-setup/audio-stack-options.md`
