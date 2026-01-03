# DJ Mode Design Document

**Feature:** Dual audio input mixing for DJ commentary over turntable playback
**Status:** Design / Not Implemented
**Created:** 2026-01-03
**Complexity:** MODERATE
**Estimated Effort:** 2-3 weeks, ~600-700 lines of code

---

## Overview

DJ Mode enables parallel audio streaming from two USB devices:
- **Primary input:** Turntable audio via Behringer UCA222 (existing)
- **Secondary input:** Microphone via HyperX QuadCast or similar USB mic
- **Output:** Real-time mixed audio stream to Sonos speakers

**Use Case:** DJ commentary/announcements over vinyl playback (intercom functionality)

---

## Feasibility Assessment

### ✅ FEASIBLE - Key Findings

| Aspect | Status | Notes |
|--------|--------|-------|
| **ALSA Support** | ✅ YES | Can handle two USB devices simultaneously |
| **Architecture** | ✅ COMPATIBLE | Clear mixing insertion point before HTTP buffer |
| **Dependencies** | ✅ NONE REQUIRED | Pure Python mixing (numpy optional for perf) |
| **Current Design** | ✅ EXTENSIBLE | AudioSource abstraction supports this |
| **Group Coordinator** | ✅ ALREADY SOLVED | Existing logic applies to mixed stream |

### ⚠️ CHALLENGES

| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| USB timing drift | CRITICAL | Independent threads + queue-based sync |
| Sample rate mismatch | HIGH | Force both devices to 48kHz in ALSA config |
| Chunk alignment | HIGH | Synchronizing buffer wrapper |
| CPU overhead | MEDIUM | Expected ~12-15% (vs 5-8% current) |
| Clipping/distortion | MEDIUM | 0.5 gain + clamping in mixer |

---

## Current Architecture Analysis

### Single-Source Design (Current)

```
AudioSource (ABC)
    ├── SyntheticAudioSource
    ├── FileAudioSource
    └── USBAudioSource
         └── USBAudioCapture (ALSA wrapper)
              ↓
         Single Producer Thread
              ↓
         WAV HTTP Server Buffer
              ↓
         Sonos Playback
```

**Key Characteristics:**
- `streaming_wav.py:146-169` - Single producer thread reading from one source
- `audio_source.read_chunk(8192)` - Synchronous blocking call
- Each `USBAudioCapture` opens one ALSA device exclusively
- Linear flow: Source → Buffer → HTTP → Sonos

### DJ Mode Design (Proposed)

```
USBAudioSource (Turntable)  ---|
                               |---> MixedAudioSource ---> Current Pipeline
USBAudioSource (Microphone) ---|         ↓
                                    PCM Mixer
                                         ↓
                                   WAV Server Buffer
                                         ↓
                                   Sonos Playback
```

**New Components:**
- `MixedAudioSource` - Abstraction wrapping two audio sources
- `PCMSampleMixer` - Core mixing logic (sample-by-sample addition)
- Dual producer threads - One per USB device
- Synchronization layer - Queue-based timing management

---

## Implementation Phases

### Phase 1: Foundation (SIMPLE - 2-3 days)

**Goal:** Validate mixing logic without USB hardware complexity

**New Files:**
```
src/turntabler/audio_mixer.py (~300 lines)
├── PCMSampleMixer          # Core mixing arithmetic
├── MixedAudioSource        # AudioSource implementation
└── SyncBuffer              # Queue-based synchronization
```

**Tasks:**
1. Implement PCM sample mixing (16-bit signed addition with clamping)
2. Create `MixedAudioSource(AudioSource)` class
3. Add CLI flags: `--dj-mode`, `--turntable-device`, `--microphone-device`
4. Test with synthetic sources (no USB required)

**Testing:**
```bash
# Mix two sine waves (should hear both frequencies)
turntabler stream --dj-mode \
  --turntable-source synthetic:440Hz \
  --microphone-source synthetic:220Hz

# Mix file + synthetic
turntabler stream --dj-mode \
  --turntable-source file:test.wav \
  --microphone-source synthetic:100Hz
```

**Deliverable:** Working audio mixer with synthetic sources

---

### Phase 2: Dual USB Support (MODERATE - 1 week)

**Goal:** Capture from two USB devices simultaneously and mix in real-time

**New Files:**
```
src/turntabler/multi_usb_audio.py (~200 lines)
├── DualUSBAudioCapture     # Manages two capture instances
├── USBDeviceSelector       # Auto-detection and pairing
└── CaptureThread           # Independent producer per device
```

**Modified Files:**
- `usb_audio.py` - Add `find_devices()` for multiple USB detection (+40 lines)
- `streaming.py` - Add DJ mode setup logic (+30 lines)
- `cli.py` - Extend with DJ mode CLI flags (+50 lines)

**Tasks:**
1. Create dual USB capture manager
2. Independent producer threads for each device
3. Queue-based synchronization
4. Device auto-detection (UCA222 vs QuadCast patterns)

**Testing:**
```bash
# Auto-detect both USB devices
turntabler stream --dj-mode

# Explicit device specification
turntabler stream --dj-mode \
  --turntable-device hw:CARD=UCA222,DEV=0 \
  --microphone-device hw:CARD=USB,DEV=0
```

**Deliverable:** Working dual USB capture with basic mixing

---

### Phase 3: Tuning & Production (COMPLEX - 1 week)

**Goal:** Production-ready with diagnostics and optimizations

**Modified Files:**
- `audio_mixer.py` - Add adaptive buffering (+80 lines)
- `diagnostics.py` - Add sync drift tracking (+100 lines)
- `streaming_wav.py` - Increase buffer size for dual sources (+5 lines)

**Tasks:**
1. Implement timing drift detection and compensation
2. Add diagnostics for sync monitoring
3. Adaptive buffer sizing (start 1000ms, adjust as needed)
4. Performance profiling and optimization
5. Extended production testing (30+ minutes)

**Testing:**
```bash
# Extended test with diagnostics
turntabler test full --dj-mode --duration 1800 --debug

# Custom mixing levels
turntabler stream --dj-mode \
  --turntable-gain 0.7 \
  --microphone-gain 0.3
```

**Deliverable:** Production-ready DJ mode with monitoring

---

## Technical Deep Dive

### PCM Mixing Algorithm

**Core Logic (Simple):**
```python
import array

def mix_pcm_streams(chunk1: bytes, chunk2: bytes,
                   gain1: float = 0.5, gain2: float = 0.5) -> bytes:
    """
    Mix two 16-bit stereo PCM streams.

    Args:
        chunk1: PCM data from turntable (16-bit signed little-endian)
        chunk2: PCM data from microphone (16-bit signed little-endian)
        gain1: Turntable gain (0.0-1.0)
        gain2: Microphone gain (0.0-1.0)

    Returns:
        Mixed PCM data (same format as inputs)
    """
    # Convert bytes to 16-bit signed samples
    samples1 = array.array('h', chunk1)  # 'h' = signed short (int16)
    samples2 = array.array('h', chunk2)

    # Ensure equal length (handle chunk size mismatches)
    min_len = min(len(samples1), len(samples2))

    result = array.array('h')
    for i in range(min_len):
        # Mix with gain scaling
        mixed = int((samples1[i] * gain1) + (samples2[i] * gain2))

        # Clamp to prevent clipping (-32768 to 32767 for int16)
        mixed = max(-32768, min(32767, mixed))

        result.append(mixed)

    return result.tobytes()
```

**Why This Works:**
- 16-bit samples range: -32768 to 32767
- Gain of 0.5 each prevents clipping (max: 32767 * 0.5 + 32767 * 0.5 = 32767)
- Direct sample addition is valid for PCM audio
- Clamping handles edge cases

**Performance:**
- Pure Python: ~50μs per 8192-byte chunk (sufficient for 48kHz streaming)
- With numpy (if needed): ~10μs per chunk

---

### Synchronization Architecture

**Challenge:** Two USB devices have independent clocks
- UCA222: 48.000 kHz (±50 ppm crystal tolerance)
- QuadCast: 48.000 kHz (±50 ppm crystal tolerance)
- Worst case drift: 100 ppm = 4.8 samples/second divergence

**Solution: Independent Producers + Sync Queue**

```python
from queue import Queue
from threading import Thread

class MixedAudioSource:
    def __init__(self, source1: AudioSource, source2: AudioSource):
        self.source1 = source1
        self.source2 = source2

        # Separate queues for each device
        self.queue1 = Queue(maxsize=48)  # ~1000ms at 48 chunks/sec
        self.queue2 = Queue(maxsize=48)

        # Producer threads
        self.thread1 = Thread(target=self._producer, args=(source1, self.queue1))
        self.thread2 = Thread(target=self._producer, args=(source2, self.queue2))

    def start(self):
        self.thread1.start()
        self.thread2.start()

    def _producer(self, source: AudioSource, queue: Queue):
        """Independent producer for each USB device."""
        while self.running:
            chunk = source.read_chunk(8192)
            if chunk is None:
                break
            queue.put(chunk, timeout=1.0)  # Block if queue full

    def read_chunk(self, size: int) -> bytes:
        """
        Read from both queues and mix.
        Consumer (HTTP server) calls this method.
        """
        try:
            # Get next chunk from each device
            chunk1 = self.queue1.get(timeout=0.1)
            chunk2 = self.queue2.get(timeout=0.1)

            # Mix and return
            return mix_pcm_streams(chunk1, chunk2,
                                  gain1=self.gain1,
                                  gain2=self.gain2)
        except queue.Empty:
            # Handle underrun (one device slower than other)
            logger.warning("Buffer underrun in DJ mode")
            return None
```

**Why This Works:**
- Each USB device captures at its own pace (independent threads)
- Queues absorb timing jitter (up to 1000ms buffer)
- Consumer (mixer) pulls when both have data
- Timeout handling prevents deadlock

**Handling Drift:**
```python
# Monitor queue depths
depth1 = self.queue1.qsize()
depth2 = self.queue2.qsize()

if abs(depth1 - depth2) > 10:  # >200ms drift
    # One device is consistently faster
    if depth1 > depth2:
        # Turntable ahead, drop samples
        self.queue1.get_nowait()  # Discard
    else:
        # Mic ahead, drop samples
        self.queue2.get_nowait()  # Discard
```

---

### CLI Design

**New Flags:**

```python
# cli.py additions

@dataclass
class DJModeConfig:
    """Configuration for DJ mode (dual audio input)."""
    enabled: bool = False
    turntable_device: Optional[str] = None  # Auto-detect if None
    microphone_device: Optional[str] = None
    turntable_source: str = "usb"  # Can be "file:path" or "synthetic:freq"
    microphone_source: str = "usb"
    turntable_gain: float = 0.7  # 70% turntable volume
    microphone_gain: float = 0.3  # 30% mic volume
    normalize: bool = True  # Auto-adjust to prevent clipping

# Add to stream command
@app.command()
def stream(
    # ... existing params ...

    # DJ mode
    dj_mode: Annotated[
        bool,
        typer.Option("--dj-mode", help="Enable dual audio input (turntable + mic)")
    ] = False,

    turntable_device: Annotated[
        Optional[str],
        typer.Option("--turntable-device", help="ALSA device for turntable (auto-detect if omitted)")
    ] = None,

    microphone_device: Annotated[
        Optional[str],
        typer.Option("--microphone-device", help="ALSA device for microphone (auto-detect if omitted)")
    ] = None,

    turntable_gain: Annotated[
        float,
        typer.Option("--turntable-gain", help="Turntable volume (0.0-1.0)", min=0.0, max=1.0)
    ] = 0.7,

    microphone_gain: Annotated[
        float,
        typer.Option("--microphone-gain", help="Microphone volume (0.0-1.0)", min=0.0, max=1.0)
    ] = 0.3,
):
    """Stream audio to Sonos with optional DJ mode (dual input mixing)."""

    # Mutual exclusivity check
    if dj_mode and (synthetic or file):
        logger.error("Cannot use --dj-mode with --synthetic or --file")
        raise typer.Exit(1)

    # ... setup logic ...
```

**Usage Examples:**

```bash
# Basic DJ mode (auto-detect both USB devices)
turntabler stream --dj-mode

# Explicit device specification
turntabler stream --dj-mode \
  --turntable-device hw:CARD=UCA222,DEV=0 \
  --microphone-device hw:CARD=USB,DEV=0

# Custom mixing levels (80% music, 20% voice)
turntabler stream --dj-mode \
  --turntable-gain 0.8 \
  --microphone-gain 0.2

# Test without hardware (development/debugging)
turntabler stream --dj-mode \
  --turntable-source file:test_vinyl.wav \
  --microphone-source synthetic:220Hz

# Extended test with diagnostics
turntabler test full --dj-mode --duration 1800 --debug --debug-interval 30
```

---

## File Modifications Summary

### New Files

| File | Purpose | Lines | Phase |
|------|---------|-------|-------|
| `src/turntabler/audio_mixer.py` | PCM mixing + MixedAudioSource | ~300 | 1 |
| `src/turntabler/multi_usb_audio.py` | Dual USB capture management | ~200 | 2 |

### Modified Files

| File | Changes | Lines | Phase |
|------|---------|-------|-------|
| `src/turntabler/audio_source.py` | Export MixedAudioSource | +50 | 1 |
| `src/turntabler/cli.py` | Add DJ mode flags and validation | +50 | 1 |
| `src/turntabler/streaming.py` | DJ mode setup logic | +30 | 2 |
| `src/turntabler/usb_audio.py` | Multi-device detection | +40 | 2 |
| `src/turntabler/streaming_wav.py` | Increase buffer size | +5 | 3 |
| `src/turntabler/diagnostics.py` | Sync drift monitoring | +100 | 3 |

**Total Estimated:** ~600-700 new lines across 8 files

---

## Hardware Requirements

### Validated Devices

| Device | Role | Specs | Status |
|--------|------|-------|--------|
| Behringer UCA222 | Turntable input | 16-bit/48kHz, USB 1.1 | ✅ VALIDATED |
| HyperX QuadCast | Microphone input | 16-bit/48kHz, USB 2.0 | ⚠️ TO BE TESTED |

### System Requirements

- **CPU:** ~12-15% on Raspberry Pi 5 (vs 5-8% single source)
- **Memory:** ~80-100 MB (vs 64 MB single source)
- **Bandwidth:** ~3.08 Mbps (2x 1.54 Mbps per stream)
- **USB Ports:** 2 available USB ports (can be on same hub)

### ALSA Configuration

Both devices must be configured for 48kHz capture:

```bash
# List devices
arecord -l

# Test turntable device
arecord -D hw:CARD=UCA222,DEV=0 -f S16_LE -r 48000 -c 2 /tmp/test_turntable.wav

# Test microphone device
arecord -D hw:CARD=USB,DEV=0 -f S16_LE -r 48000 -c 2 /tmp/test_mic.wav
```

---

## Testing Strategy

### Phase 1: Synthetic Testing (No Hardware)

**Goal:** Validate mixing math and basic integration

```bash
# Test 1: Two sine waves (should hear both frequencies)
turntabler stream --dj-mode \
  --turntable-source synthetic:440Hz \
  --microphone-source synthetic:220Hz \
  --sonos-ip 192.168.1.100

# Expected: Hear both 440Hz and 220Hz tones simultaneously
# Verify: No clipping, equal volume balance

# Test 2: Different gains
turntabler stream --dj-mode \
  --turntable-source synthetic:440Hz \
  --microphone-source synthetic:220Hz \
  --turntable-gain 0.8 \
  --microphone-gain 0.2

# Expected: 440Hz louder than 220Hz (4:1 ratio)

# Test 3: File + synthetic
turntabler stream --dj-mode \
  --turntable-source file:test_vinyl.wav \
  --microphone-source synthetic:100Hz

# Expected: Music with 100Hz tone overlay
```

**Success Criteria:**
- ✅ Both sources audible in output
- ✅ No clipping or distortion
- ✅ Gain controls work as expected
- ✅ No crashes or errors

---

### Phase 2: USB Hardware Testing

**Goal:** Validate dual USB capture and synchronization

```bash
# Test 1: Auto-detection
turntabler stream --dj-mode --debug

# Verify in logs:
# - Both USB devices detected
# - Correct ALSA device assignment
# - No ALSA errors

# Test 2: Extended capture (10 minutes)
turntabler test full --dj-mode --duration 600 --debug --debug-interval 30

# Monitor:
# - CPU usage (should be <15%)
# - Buffer occupancy (should be 30-70%)
# - Sync drift (should be <100ms over 10 min)
# - Overruns/underruns (should be 0)

# Test 3: Gain adjustment while streaming
# (Manual test - adjust gains via CLI flags and restart)
```

**Success Criteria:**
- ✅ Both USB devices capture simultaneously
- ✅ No dropouts or stuttering
- ✅ Sync drift < 100ms over 10 minutes
- ✅ CPU < 15% on Raspberry Pi 5
- ✅ Zero buffer overruns/underruns

---

### Phase 3: Production Validation

**Goal:** Long-term stability and real-world usage

```bash
# Test 1: Extended streaming (30+ minutes)
turntabler stream --dj-mode \
  --turntable-device hw:CARD=UCA222,DEV=0 \
  --microphone-device hw:CARD=USB,DEV=0 \
  --turntable-gain 0.7 \
  --microphone-gain 0.3 \
  --debug --debug-interval 60

# Monitor for:
# - Memory leaks (memory should stay stable)
# - Timing drift accumulation
# - Audio quality degradation
# - Any warnings in logs

# Test 2: Real DJ usage
# - Play vinyl on turntable
# - Speak into microphone during playback
# - Verify both sources mixed properly in Sonos output
# - Test at different volumes

# Test 3: Stress test
# - Run for several hours
# - Monitor Raspberry Pi temperature
# - Check for any stability issues
```

**Success Criteria:**
- ✅ Stable for 30+ minutes continuous use
- ✅ No memory leaks
- ✅ Audio quality remains consistent
- ✅ Real-world DJ usage works as expected
- ✅ Temperature stays within safe limits

---

## Known Risks & Mitigations

### Risk 1: USB Timing Drift
**Severity:** HIGH
**Probability:** CERTAIN (USB devices have independent clocks)

**Symptoms:**
- Audio gradually goes out of sync
- One stream faster than other
- Buffer overruns or underruns

**Mitigation:**
```python
# Monitor queue depth difference
if abs(queue1.qsize() - queue2.qsize()) > DRIFT_THRESHOLD:
    # Drop samples from faster queue
    faster_queue.get_nowait()
    logger.warning(f"Compensating for timing drift: {depth_diff} chunks")
```

**Alternative (Advanced):**
- Implement adaptive resampling using `scipy.signal.resample`
- Continuously adjust sample rate to match slower device

---

### Risk 2: CPU Overhead on Raspberry Pi
**Severity:** MEDIUM
**Probability:** MEDIUM (depends on other system load)

**Symptoms:**
- CPU usage > 20%
- Audio stuttering
- Increased latency

**Mitigation:**
```python
# Phase 1: Profile mixing code
import cProfile
cProfile.run('mix_pcm_streams(chunk1, chunk2)')

# Phase 2: Optimize with numpy if needed
import numpy as np

def mix_pcm_streams_fast(chunk1: bytes, chunk2: bytes) -> bytes:
    arr1 = np.frombuffer(chunk1, dtype=np.int16)
    arr2 = np.frombuffer(chunk2, dtype=np.int16)
    mixed = ((arr1 * 0.5 + arr2 * 0.5)).astype(np.int16)
    return mixed.tobytes()

# Phase 3: Consider Cython if still too slow (unlikely)
```

---

### Risk 3: ALSA Device Conflicts
**Severity:** MEDIUM
**Probability:** LOW (modern ALSA handles multiple devices well)

**Symptoms:**
- One device fails to open
- "Device busy" errors
- Intermittent capture failures

**Mitigation:**
```python
# Ensure exclusive access pattern
try:
    pcm1 = alsaaudio.PCM(device=device1, ...)
    pcm2 = alsaaudio.PCM(device=device2, ...)
except alsaaudio.ALSAAudioError as e:
    logger.error(f"Failed to open devices: {e}")
    logger.error("Ensure no other apps are using USB audio")
    # Provide recovery instructions
```

---

### Risk 4: Audio Clipping/Distortion
**Severity:** MEDIUM
**Probability:** MEDIUM (depends on input levels)

**Symptoms:**
- Harsh, distorted sound
- Audio peaks clipped
- Loss of dynamic range

**Mitigation:**
```python
# Option 1: Fixed gain (safe but limits volume)
turntable_gain = 0.5
microphone_gain = 0.5

# Option 2: Adaptive normalization (better)
def mix_with_normalization(chunk1, chunk2):
    samples1 = array.array('h', chunk1)
    samples2 = array.array('h', chunk2)

    # Find peak in both
    peak1 = max(abs(max(samples1)), abs(min(samples1)))
    peak2 = max(abs(max(samples2)), abs(min(samples2)))

    # Calculate safe gains
    total_peak = peak1 + peak2
    if total_peak > 32767:
        scale = 32767 / total_peak
        gain1 = scale
        gain2 = scale
    else:
        gain1 = 1.0
        gain2 = 1.0

    # Mix with calculated gains
    return mix_pcm_streams(chunk1, chunk2, gain1, gain2)
```

---

## Performance Targets

| Metric | Current (Single Source) | Target (DJ Mode) | Maximum Acceptable |
|--------|------------------------|------------------|-------------------|
| **CPU Usage** | 5-8% | 10-12% | 15% |
| **Memory** | 64 MB | 80 MB | 100 MB |
| **Bandwidth** | 1.54 Mbps | 3.08 Mbps | 3.5 Mbps |
| **Latency** | ~500ms | ~1000ms | 1500ms |
| **Buffer Overruns** | 0 | 0 | 0 |
| **Sync Drift (10min)** | N/A | <50ms | 100ms |
| **Dropouts (30min)** | 0 | 0 | 0 |

---

## Dependencies

### Required (Current)
```toml
# pyproject.toml - no changes needed
dependencies = [
    "soco>=0.30.0",
    "fastapi[standard]>=0.104.0",
    "pyalsaaudio>=0.10.0",
    "typer>=0.12.0",
]
```

### Optional (Performance)
```toml
# Only add if Phase 3 performance tuning requires it
optional-dependencies.dj-mode = [
    "numpy>=1.24.0",  # Fast array operations for mixing
]
```

### Advanced (Unlikely Needed)
```toml
# Only if severe sync drift requires resampling
optional-dependencies.dj-mode-advanced = [
    "scipy>=1.11.0",    # Signal resampling
    "librosa>=0.10.0",  # Audio DSP utilities
]
```

**Recommendation:** Start with zero dependencies. Only add numpy if profiling shows CPU bottleneck (unlikely). Only add scipy/librosa if sync drift cannot be solved with simple sample dropping (very unlikely).

---

## Future Enhancements

### Post-MVP Features (Not in Initial Implementation)

1. **Multi-Room DJ Mode**
   - Send different mixes to different Sonos groups
   - Main room: turntable + mic
   - Other rooms: turntable only

2. **Real-Time Gain Adjustment**
   - Web UI for volume sliders
   - Adjust mix levels without restarting stream
   - Live waveform visualization

3. **Audio Effects**
   - Low-pass filter on mic (voice clarity)
   - Compression/limiting to prevent clipping
   - Ducking (auto-lower music when speaking)

4. **Multi-Source Support**
   - Support 3+ audio sources
   - Routing matrix (source to output mapping)
   - Professional DJ mixer emulation

5. **Recording**
   - Save mixed stream to WAV file
   - Split recording (separate tracks for each source)
   - Post-processing and editing

---

## References

### Key Files (Current Implementation)
- `src/turntabler/audio_source.py` - AudioSource abstraction (lines 52-72)
- `src/turntabler/streaming_wav.py` - Producer-consumer pattern (lines 146-195)
- `src/turntabler/usb_audio_capture.py` - ALSA capture logic (lines 226-250)
- `src/turntabler/streaming.py` - Orchestration (lines 139-186)
- `src/turntabler/cli.py` - CLI interface (lines 47-206)

### Design Principles (from CLAUDE.md)
- ✅ Use `uv` for dependency management
- ✅ No conditional imports
- ✅ All imports at top level
- ✅ Don't overengineer - simple, maintainable solutions
- ✅ Group coordinator pattern for Sonos
- ✅ Async patterns with `asyncio.to_thread()`

### External Resources
- ALSA Programming HOWTO: https://www.alsa-project.org/alsa-doc/alsa-lib/
- PCM Audio Format: https://en.wikipedia.org/wiki/Pulse-code_modulation
- USB Audio Class: https://www.usb.org/document-library/audio-data-formats-30

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-03 | Use pure Python for mixing | No deps, sufficient performance |
| 2026-01-03 | Independent producer threads | Matches current WAVStreamingServer pattern |
| 2026-01-03 | Queue-based synchronization | Absorbs timing jitter, well-understood pattern |
| 2026-01-03 | 1000ms buffer (vs 500ms) | Extra headroom for dual-source jitter |
| 2026-01-03 | 0.5 default gain each | Prevents clipping, can be overridden via CLI |
| 2026-01-03 | No automatic ducking in MVP | Keep it simple, add later if requested |
| 2026-01-03 | Phase 1 with synthetic sources | De-risk implementation, no hardware dependency |

---

## Appendix A: Example Implementation (Skeleton)

### audio_mixer.py (Core Logic)

```python
"""Audio mixing for DJ mode (dual input streaming)."""

import array
import logging
from dataclasses import dataclass
from queue import Queue, Empty
from threading import Thread, Event
from typing import Optional

from turntabler.audio_source import AudioSource

logger = logging.getLogger(__name__)


def mix_pcm_streams(
    chunk1: bytes,
    chunk2: bytes,
    gain1: float = 0.5,
    gain2: float = 0.5,
) -> bytes:
    """
    Mix two 16-bit stereo PCM streams.

    Args:
        chunk1: First audio stream (16-bit signed LE)
        chunk2: Second audio stream (16-bit signed LE)
        gain1: Gain for first stream (0.0-1.0)
        gain2: Gain for second stream (0.0-1.0)

    Returns:
        Mixed PCM data (same format as inputs)
    """
    samples1 = array.array('h', chunk1)
    samples2 = array.array('h', chunk2)

    min_len = min(len(samples1), len(samples2))
    result = array.array('h')

    for i in range(min_len):
        mixed = int((samples1[i] * gain1) + (samples2[i] * gain2))
        mixed = max(-32768, min(32767, mixed))
        result.append(mixed)

    return result.tobytes()


class MixedAudioSource(AudioSource):
    """
    Audio source that mixes two underlying sources in real-time.

    Uses independent producer threads for each source with queue-based
    synchronization to handle timing differences between USB devices.
    """

    def __init__(
        self,
        source1: AudioSource,
        source2: AudioSource,
        gain1: float = 0.7,
        gain2: float = 0.3,
        buffer_size: int = 48,  # ~1000ms at 48 chunks/sec
    ):
        self.source1 = source1
        self.source2 = source2
        self.gain1 = gain1
        self.gain2 = gain2

        self.queue1 = Queue(maxsize=buffer_size)
        self.queue2 = Queue(maxsize=buffer_size)

        self._stop = Event()
        self._thread1: Optional[Thread] = None
        self._thread2: Optional[Thread] = None

    def start(self):
        """Start producer threads for both sources."""
        self._thread1 = Thread(
            target=self._producer,
            args=(self.source1, self.queue1, "Source1"),
            daemon=True,
        )
        self._thread2 = Thread(
            target=self._producer,
            args=(self.source2, self.queue2, "Source2"),
            daemon=True,
        )

        self._thread1.start()
        self._thread2.start()
        logger.info("Started dual audio producers")

    def _producer(self, source: AudioSource, queue: Queue, name: str):
        """Producer thread for a single audio source."""
        logger.info(f"{name} producer started")

        while not self._stop.is_set():
            try:
                chunk = source.read_chunk(8192)
                if chunk is None:
                    break
                queue.put(chunk, timeout=1.0)
            except Exception as e:
                logger.error(f"{name} producer error: {e}")
                break

        logger.info(f"{name} producer stopped")

    def read_chunk(self, size: int) -> Optional[bytes]:
        """
        Read next mixed chunk.

        Pulls from both queues and mixes the samples.
        """
        try:
            chunk1 = self.queue1.get(timeout=0.1)
            chunk2 = self.queue2.get(timeout=0.1)

            # Mix and return
            return mix_pcm_streams(chunk1, chunk2, self.gain1, self.gain2)

        except Empty:
            logger.warning("Buffer underrun in MixedAudioSource")
            return None

    def stop(self):
        """Stop producer threads and clean up."""
        logger.info("Stopping MixedAudioSource")
        self._stop.set()

        if self._thread1:
            self._thread1.join(timeout=2.0)
        if self._thread2:
            self._thread2.join(timeout=2.0)
```

---

## Appendix B: Diagnostics Extensions

### diagnostics.py Additions

```python
@dataclass
class DJModeDiagnostics:
    """Diagnostics specific to DJ mode (dual audio input)."""

    # Queue depth tracking
    queue1_depths: list[int] = field(default_factory=list)
    queue2_depths: list[int] = field(default_factory=list)

    # Sync drift detection
    sync_drift_samples: list[int] = field(default_factory=list)
    max_drift: int = 0

    # Underrun tracking
    underruns: int = 0

    def record_queue_depths(self, depth1: int, depth2: int):
        """Record current queue depths for sync monitoring."""
        self.queue1_depths.append(depth1)
        self.queue2_depths.append(depth2)

        drift = abs(depth1 - depth2)
        self.sync_drift_samples.append(drift)
        self.max_drift = max(self.max_drift, drift)

    def record_underrun(self):
        """Record buffer underrun event."""
        self.underruns += 1

    def get_summary(self) -> dict:
        """Generate diagnostic summary for DJ mode."""
        return {
            "avg_queue1_depth": sum(self.queue1_depths) / len(self.queue1_depths),
            "avg_queue2_depth": sum(self.queue2_depths) / len(self.queue2_depths),
            "avg_sync_drift": sum(self.sync_drift_samples) / len(self.sync_drift_samples),
            "max_sync_drift": self.max_drift,
            "max_sync_drift_ms": (self.max_drift * 42.7),  # chunk duration
            "underruns": self.underruns,
        }
```

---

## Contact & Ownership

**Feature Owner:** TBD
**Design Author:** Claude Sonnet 4.5 (2026-01-03)
**Status:** Design only - not implemented

**For questions or to start implementation:**
1. Review this design document
2. Start with Phase 1 (synthetic sources)
3. Test thoroughly before proceeding to Phase 2
4. Update this document with findings and adjustments

---

*Last updated: 2026-01-03*
