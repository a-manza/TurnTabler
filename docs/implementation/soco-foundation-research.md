# SoCo & Sonos Streaming Foundation Research

**Date:** 2025-11-14
**Purpose:** Establish deep understanding of how SoCo works and Sonos streaming mechanisms
**Status:** Research complete - ready for POC debugging

---

## Core Understanding: What SoCo Actually Does

### The Critical Insight

**SoCo is NOT a streaming library.** It's a control library that tells Sonos where to fetch audio from.

```
Your HTTP Server (FastAPI)  ←  serves audio files/streams
       ↓
SoCo (play_uri call)  ←  tells Sonos the URL
       ↓
Sonos Device  ←  makes HTTP GET requests to fetch the audio
       ↓
Speaker  ←  plays the audio
```

**This means:**
1. SoCo only manages the instruction ("go play this URL")
2. Actual audio delivery is HTTP from your server to Sonos
3. You need both SoCo (control) AND HTTP server (streaming)

---

## Key SoCo APIs for Streaming

### play_uri() Method

```python
sonos_device.play_uri(
    'http://server:8000/audio.flac',  # Where Sonos fetches audio
    title='My Audio',                   # Display metadata
    force_radio=True                    # CRITICAL parameter!
)
```

### What force_radio=True Does

**Critical Discovery:** Modern Sonos firmware (v6.4.2+) no longer accepts standard HTTP/HTTPS URIs for streaming.

When `force_radio=True`:
- Converts `http://` → `x-rincon-mp3radio://` URI scheme
- Converts `https://` → `x-rincon-mp3radio://` URI scheme
- Treats stream as "radio" format (continuous, indefinite)
- Uses different buffering and timeout logic
- **This is MANDATORY for continuous turntable streaming**

Without `force_radio=True`:
- Expects finite file with known length
- May timeout on infinite streams
- Not suitable for live audio sources

---

## Sonos Audio Format Support

### Official Specifications

| Format | Bit Depth | Sample Rate | Channels | Status |
|--------|-----------|-------------|----------|--------|
| FLAC   | 16-bit    | ≤48 kHz     | Mono/Stereo | ✅ Official |
| WAV    | 16-bit    | ≤48 kHz     | Mono/Stereo | ✅ Official |
| AIFF   | 16-bit    | ≤48 kHz     | Mono/Stereo | ✅ Official |
| ALAC   | 16-bit    | ≤48 kHz     | Mono/Stereo | ✅ Official |
| MP3    | -         | ≤48 kHz     | Mono/Stereo | ✅ Official |

### Critical Limitation

- **Maximum sample rate: 48 kHz**
- 96 kHz and 192 kHz **NOT supported**
- 24-bit may be internally truncated to 16-bit
- Multi-channel (5.1, 7.1) **NOT supported**

**For turntable:** 48kHz/16-bit/2-channel is ideal

---

## FLAC Encoding for Sonos

### Frame Size Matters

Sonos recommends frame sizes ≤ 32 KB:

```
Frame Size = (blocksize × bit_depth × channels) ÷ 8

Example: 4096 samples × 16 bits × 2 channels ÷ 8 = 16 KB ✅
Example: 8192 samples × 16 bits × 2 channels ÷ 8 = 32 KB ✅
Example: 16384 samples × 16 bits × 2 channels ÷ 8 = 64 KB ❌
```

### Metadata Position Affects Streaming

- **Metadata at beginning:** Sonos reads it quickly, streams efficiently
- **Metadata at end:** Sonos seeks to end first, then back to start = extra requests
- **Modern encoders:** Default to beginning (ffmpeg, sox both do this)

### Seek Table

- **Present:** Reduces HTTP requests by ~50%
- **Missing:** More repeated requests (still works, just less efficient)
- **Recommendation:** Include seek table for optimal streaming

---

## How Sonos Buffers Audio

### The Repeated Requests Pattern

You observed: Sonos making multiple requests for the same file.

This is **normal and expected behavior.**

**How it works:**

1. **First request:** `GET /turntable.flac HTTP/1.1`
   - Sonos begins downloading from position 0
   - Starts buffering while playing
   - Gets metadata from file beginning

2. **As buffer depletes:** Sonos makes range request
   - `GET /turntable.flac HTTP/1.1 Range: bytes=65536-131072`
   - Fetches next chunk
   - Continues playing

3. **Pattern continues:** Until file ends or stream is stopped

**This is NOT an error.** It's the streaming protocol at work.

---

## Protocol Layers: Control vs Streaming

### Layer 1: Control Protocol (SoCo manages)

```
Your Python Code
    ↓
SoCo library
    ↓
UPnP/SOAP Protocol
    ↓
Sonos Device Control Port (1400)
    ↓
Device responds with status XML
```

**Purpose:** Tell Sonos what to do (play, pause, stop, what URL to fetch)
**Technology:** SOAP over HTTP POST
**SoCo handles:** All of this automatically

### Layer 2: Streaming Protocol (Your HTTP server manages)

```
Sonos Device
    ↓
HTTP GET Requests
    ↓
Your HTTP Server (FastAPI)
    ↓
FLAC/WAV Audio Data
    ↓
Back to Sonos Device
```

**Purpose:** Deliver actual audio data
**Technology:** Standard HTTP GET with optional Range headers
**You handle:** Serving files correctly with proper headers

**These are separate layers.** SoCo doesn't manage streaming - it only initiates it.

---

## Why Quality Difference: AirPlay vs Sonos Native

### AirPlay Path (Lossy) - OwnTone

```
Turntable Audio
    ↓
OwnTone (AirPlay Server)
    ↓
AirPlay 2 Protocol
    ↓
Sonos Beam (receives as AAC-LC)
    ↓
❌ LOSSY - AAC-LC is lossy compression
```

### Sonos Native Path (Lossless) - SoCo

```
Turntable Audio
    ↓
FLAC Encoding (lossless)
    ↓
HTTP Server (SoCo initiates playback)
    ↓
Sonos Beam (fetches FLAC via HTTP)
    ↓
✅ LOSSLESS - FLAC codec preserved all the way
```

**The difference:** What codec Sonos actually plays
- AirPlay: Forces to AAC-LC (lossy)
- Sonos Native: Preserves FLAC (lossless)

---

## The "PLAYING but No Audio" Problem

When Sonos shows "PLAYING" status but you hear no audio:

### Likely Causes (in order of probability)

1. **Volume Issue** (Most common)
   - Device muted
   - Volume at 0%
   - Wrong speaker selected (grouped differently)

2. **FLAC Encoding Issue**
   - Frame size > 32 KB
   - Sample rate > 48 kHz (e.g., 96 kHz)
   - Unsupported bit depth
   - Corrupted metadata

3. **File Delivery Issue**
   - HTTP server error (not responding to Range requests)
   - File incomplete or truncated
   - Wrong MIME type

4. **Network Issue**
   - WiFi latency causing timeout
   - Network buffer too small
   - Firewall blocking audio streaming

5. **Device State Issue**
   - Device in wrong state (grouped, airplay active, etc.)
   - Firmware bug (rare)

### Systematic Debugging Approach

This is why we recommend:
1. **Test with known-working URI** (BBC Radio) → Proves infrastructure
2. **Test with WAV format** → Eliminates FLAC encoding issues
3. **Check volume/mute** → Most common issue
4. **Monitor server logs** → See actual HTTP requests
5. **Verify FLAC specs** → Match Sonos requirements

---

## Expected HTTP Request Patterns

### Healthy Continuous Stream

```
[0s] Client: Sonos, GET /turntable.flac
[0.1s] Server: 200 OK (starts sending data)
[1s] Client: Range request for next chunk
[1.5s] Client: Range request for next chunk
... continues indefinitely or until stopped
```

### What We Observed in Your Test

```
📁 Serving test-loop.flac (437608 bytes)
INFO: 192.168.86.63:54198 - "GET /turntable.flac HTTP/1.1" 200 OK
📁 Serving test-loop.flac (437608 bytes)
INFO: 192.168.86.63:54200 - "GET /turntable.flac HTTP/1.1" 200 OK
[... repeated multiple times ...]
```

**Analysis:**
- Multiple complete re-requests (not range requests)
- Suggests possible:
  - FLAC metadata issues (needs re-reading)
  - Sonos seeking to end and back to start
  - Or simply rapid buffering pattern

**This pattern alone doesn't indicate a problem.** Could be normal behavior for this FLAC file's metadata structure.

---

## Latency Considerations

### Turntable Streaming Requirements

- **Acceptable for turntable:** < 1 second (no interactive controls needed)
- **Typical AirPlay:** 200-300 ms (proven)
- **Typical Sonos Native:** Unknown (needs testing)

**Why different latency paths?**
- AirPlay: Standardized, consistent protocol
- Sonos Native: Custom, varies by firmware and network

This is exactly what your POC is designed to measure.

---

## What We Know Works

### Internet Radio with SoCo

SoCo users successfully stream:
- Internet radio streams (continuous)
- Spotify via web (continuous)
- Cloud music services (continuous)

All use `force_radio=True` with HTTP/HTTPS URIs pointing to remote servers.

**This proves:**
- SoCo can handle continuous streams ✓
- x-rincon-mp3radio:// protocol works ✓
- HTTP streaming to Sonos works ✓

The only unknown: Does it work with LOCAL HTTP servers? (That's your POC)

---

## Your POC's Purpose

You're answering these specific questions:

1. **Does Sonos accept local HTTP streams?**
   - vs remote servers (proven to work)

2. **Can continuous FLAC streams be delivered locally?**
   - vs just HTTP access to files

3. **What's the actual latency with local server?**
   - vs remote servers (200-300 ms)

4. **Is audio quality truly lossless end-to-end?**
   - FLAC preservation through entire chain

5. **Is stability acceptable for turntable?**
   - 10+ minute test without dropouts

---

## Files Involved in Your Setup

### Python Scripts (SoCo Control)

| File | Purpose | Status |
|------|---------|--------|
| `control.py` | Main SoCo interface | Created |
| `test_known_uri.py` | Test public radio | Created |
| `test_wav.py` | Test WAV format | Created |

### Python Scripts (HTTP Streaming)

| File | Purpose | Status |
|------|---------|--------|
| `streaming.py` | Looping FLAC server | Created |
| `streaming_simple.py` | One-time FLAC serve | Created |
| `streaming_debug.py` | Detailed logging | Created |

### Audio Files

| File | Format | Purpose | Status |
|------|--------|---------|--------|
| `test-loop.flac` | FLAC | Production test | Needs regeneration |
| `test-loop.wav` | WAV | Control test | To be created |

### Configuration

| File | Purpose | Status |
|------|---------|--------|
| `pyproject.toml` | Dependencies (soco, fastapi, uvicorn) | Created |
| `regenerate_test_audio.sh` | Audio file generation | Created |

---

## Next Steps

1. **Run regenerate_test_audio.sh**
   - Creates properly-specified FLAC and WAV files

2. **Follow systematic debugging in README.md**
   - Test 1: Public radio (proves infrastructure)
   - Test 2: Setup debug server (reveals patterns)
   - Test 3: FLAC format (our main test)
   - Test 4: WAV format (control test)

3. **Document findings**
   - What works/what doesn't
   - HTTP request patterns observed
   - Latency measurements
   - Quality assessment

4. **Decide next direction**
   - If SoCo works → Proceed with full implementation
   - If SoCo fails → Evaluate OwnTone fallback

---

## CRITICAL: Sonos Grouping and Playback Commands

### What is Grouping?

Sonos allows multiple speakers to be grouped together for synchronized playback:
- **Beam + Sub** → Play same audio on both
- **Room A + Room B** → Multi-room audio
- **All speakers** → Whole-home audio

### How Grouping Works

When devices are grouped:
1. One device becomes the **coordinator**
2. Other devices are **members** that follow the coordinator
3. **Playback commands must go to the coordinator**
4. Members automatically play what the coordinator plays

### The Critical SoCo Mistake

**COMMON ERROR:** Sending `play_uri()` to a member device

```python
# ❌ WRONG (if device is grouped)
beam.play_uri('http://server:8000/audio.flac')

# ✅ CORRECT (properly handles grouping)
if beam.group:
    coordinator = beam.group.coordinator
    coordinator.play_uri('http://server:8000/audio.flac')
else:
    beam.play_uri('http://server:8000/audio.flac')
```

### What Happens When You Get It Wrong

- Command appears to succeed (`play_uri()` returns without error)
- Device reports "TRANSITIONING" or "PLAYING" state
- **But no audio plays** because member device is following coordinator, not executing command
- This explains the earlier logs: "STOPPED" immediately on BBC Radio
- Very confusing for debugging

### Identifying Grouped Devices

```python
device = discover()[0]

# Check if grouped
if device.group:
    print("Device is grouped!")
    print(f"Group members: {[m.player_name for m in device.group.members]}")
    print(f"Coordinator: {device.group.coordinator.player_name}")
else:
    print("Device is standalone (not grouped)")
```

### The Fix: Always Use Coordinator

All your control scripts now include this pattern:

```python
# After discovering device
if device.group:
    playback_device = device.group.coordinator
else:
    playback_device = device

# Use playback_device for ALL playback commands
playback_device.play_uri(uri, ...)
playback_device.stop()
playback_device.pause()
playback_device.get_current_transport_info()
```

### Why This Matters for Turntable

Turntable setup typically groups speakers:
- Beam (main playback device)
- Sub (for bass)
- Potentially other rooms

**Your POC must handle grouped devices properly** or it won't work in real-world setups.

### Impact on Your POC

This fix was applied to:
- `control.py` - Main playback control
- `test_known_uri.py` - BBC Radio test
- `test_wav.py` - WAV format test
- (Any future playback scripts must follow the same pattern)

**Expected improvement:** BBC Radio test should now transition to PLAYING and produce audio

---

## Summary Table: This POC vs Real Usage

| Aspect | POC | Real Turntable |
|--------|-----|----------------|
| **Audio Source** | Generated tone | USB audio interface |
| **Server** | FastAPI (local) | Same (runs on Pi) |
| **Format** | FLAC test file | FLAC from ADC |
| **Device** | Sonos Beam | Same |
| **Protocol** | SoCo + HTTP | Same |
| **Purpose** | Validate approach | Actual vinyl streaming |

**If POC works, scaling to real turntable is straightforward:**
- Replace audio file → Replace with real audio capture
- Everything else stays the same

---

## Sources & References

- **SoCo Docs:** https://docs.python-soco.com/
- **Sonos Developer Docs:** https://docs.sonos.com/
- **Sonos FLAC Best Practices:** https://docs.sonos.com/docs/flac-best-practices
- **Sonos Audio Format Support:** https://docs.sonos.com/docs/supported-audio-formats
- **UPnP/DLNA Specification:** http://www.upnp.org/
- **Your Project Docs:** `/docs/implementation/soco-approach.md`

---

**Status:** Ready for systematic debugging. Follow the testing guide in README.md
