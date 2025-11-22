# TurnTabler: Audio Streaming Flow

How vinyl audio travels from your turntable to Sonos speakers using lossless PCM streaming.

---

## Signal Path Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Turntable  │───▶│ USB Audio   │───▶│   Linux     │───▶│  HTTP WAV   │───▶│   Sonos     │
│  (Analog)   │    │  Interface  │    │   (ALSA)    │    │   Server    │    │  Speaker    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     RCA              USB 1.1           pyalsaaudio        FastAPI            Native
   Line-out           ADC               PCM capture      Chunked HTTP        Protocol
```

---

## Stage 1: Analog to Digital Conversion

**Components:** Turntable → Preamp → USB Audio Interface (Behringer UCA222)

```
Vinyl Groove → Stylus → Cartridge → Phono Preamp → Line Level → ADC
                                                      │
                                              ┌───────┴───────┐
                                              │  USB Interface │
                                              │  (UCA222)      │
                                              │                │
                                              │  48kHz sample  │
                                              │  16-bit depth  │
                                              │  2 channels    │
                                              └───────┬───────┘
                                                      │
                                                   USB 1.1
                                                      ▼
                                                    Linux
```

**What happens:**
- Turntable outputs analog audio (typically via RCA)
- USB interface's ADC (Analog-to-Digital Converter) samples the waveform
- Produces PCM data: 48,000 samples/second × 16 bits × 2 channels = **1.536 Mbps**

---

## Stage 2: ALSA Capture

**Components:** Linux Kernel → ALSA → pyalsaaudio → Python

```python
# How TurnTabler captures audio from USB
config = CaptureConfig(
    device="hw:CARD=UCA222,DEV=0",  # ALSA hardware device
    sample_rate=48000,
    channels=2,
    sample_format=SampleFormat.S16_LE,  # 16-bit signed little-endian
    period_size=1024,   # Frames per read (~21ms)
    periods=3,          # Ring buffer depth
)
```

**ALSA Ring Buffer:**

```
┌─────────┬─────────┬─────────┐
│ Period  │ Period  │ Period  │  ← 3 periods × 1024 frames
│   0     │   1     │   2     │  ← Total: 3072 frames (~64ms buffer)
└────┬────┴────┬────┴────┬────┘
     │         │         │
   Write     Read      Next
   (ADC)   (Python)
```

**What happens:**
1. USB interface continuously fills the ring buffer via DMA
2. Python calls `pcm.read()` to pull complete periods
3. Each read returns 1024 frames = 4096 bytes (1024 × 2 channels × 2 bytes)
4. Non-blocking mode prevents stalls if data isn't ready

---

## Stage 3: HTTP WAV Streaming

**Components:** AudioSource → Jitter Buffer → WAVStreamingServer → Sonos HTTP Client

### WAV Header (Infinite Stream)

```python
def generate_wav_header():
    header = b"RIFF"
    header += struct.pack("<I", 0xFFFFFFFF)  # File size: "infinite"
    header += b"WAVE"
    header += b"fmt " + ...                   # Format chunk
    header += b"data"
    header += struct.pack("<I", 0xFFFFFFFF)  # Data size: "infinite"
    return header  # 44 bytes
```

The `0xFFFFFFFF` (4GB) signals to Sonos: "this stream has no end."

### Streaming Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ USBAudio     │     │ FastAPI      │     │ Sonos        │
│ Source       │     │ Server       │     │ Speaker      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │   read_chunk()     │                    │
       │◀───────────────────│                    │
       │                    │                    │
       │   4096 bytes       │   GET /stream.wav  │
       │───────────────────▶│◀───────────────────│
       │                    │                    │
       │                    │   WAV header       │
       │                    │───────────────────▶│
       │                    │                    │
       │                    │   Chunk (4KB)      │
       │                    │───────────────────▶│
       │                    │                    │
       │                    │   Chunk (4KB)      │
       │                    │───────────────────▶│
       │                    │         ...        │
       ▼                    ▼                    ▼
    (continuous)        (continuous)        (plays audio)
```

### HTTP Response

```http
HTTP/1.1 200 OK
Content-Type: audio/wav
Transfer-Encoding: chunked
Cache-Control: no-cache, no-store
icy-name: TurnTabler

<44 bytes WAV header>
<4096 bytes PCM data>
<4096 bytes PCM data>
...forever...
```

**Key insight:** No `Content-Length` header + chunked encoding = infinite stream.

### Jitter Buffer

To absorb WiFi latency variations and ensure smooth playback, TurnTabler uses a producer-consumer buffer:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Producer   │     │   Buffer     │     │   Consumer   │
│   Thread     │────▶│  (deque)     │────▶│   (HTTP)     │
└──────────────┘     └──────────────┘     └──────────────┘
   ALSA read           ~12 chunks           yields to
   every 42.7ms        ~500ms depth         Sonos client
```

**Why this matters:**
1. **Pre-fill before play** - Buffer fills (~500ms) before telling Sonos to connect
2. **Immediate data** - Sonos gets audio instantly when it sends GET request
3. **Jitter absorption** - WiFi latency spikes (50-100ms) don't cause skips
4. **Decoupled timing** - ALSA timing variations don't affect HTTP delivery

**Configuration:**
```python
buffer_size = 12  # chunks (~500ms at 42.7ms per chunk)
```

---

## Stage 4: Sonos Playback

**Components:** SoCo library → Sonos UPnP/SOAP → Speaker

### Connection Sequence

```python
# 1. Find the group coordinator (critical!)
if device.group:
    coordinator = device.group.coordinator
else:
    coordinator = device

# 2. Tell Sonos to fetch our stream
coordinator.play_uri(
    uri="http://192.168.1.100:5901/stream.wav",
    title="TurnTabler",
    force_radio=False  # Important: prevents metadata corruption
)
```

### What Sonos Does

1. **Receives URI** via UPnP SOAP call
2. **Opens HTTP connection** to our server
3. **Buffers** initial data (a few seconds)
4. **Decodes** WAV header, configures DAC
5. **Streams** PCM directly to speakers
6. **Maintains** connection indefinitely

```
Sonos Internal:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Network   │───▶│   Buffer    │───▶│    DAC      │───▶ Speakers
│   Stack     │    │  (seconds)  │    │  Amplifier  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Why This Works

### Why WAV (not FLAC/MP3)?
- **No end markers** - FLAC requires known file size
- **No encoding overhead** - Raw PCM, minimal CPU
- **Sonos native support** - Direct to DAC, no transcoding

### Why Native Protocol (not AirPlay)?
- **True lossless** - AirPlay uses lossy AAC-LC codec
- **Lower latency** - Direct HTTP vs Apple's buffering
- **Simpler** - No pairing, encryption, or authentication

### Audio Quality
| Spec | Value |
|------|-------|
| Sample Rate | 48,000 Hz |
| Bit Depth | 16-bit |
| Channels | 2 (stereo) |
| Bitrate | 1.536 Mbps |
| Format | PCM (uncompressed) |

This matches Sonos's maximum supported quality - your vinyl plays back exactly as captured.

---

## Timing & Latency

```
Turntable → USB Interface:     ~0ms (analog)
USB → ALSA Buffer:             ~42.7ms (period_size/sample_rate)
ALSA → Python:                 ~1ms (read call)
Python → Jitter Buffer:        ~500ms (pre-fill before play)
Buffer → HTTP Chunk:           ~0ms (memory copy)
Network → Sonos:               ~1-50ms (WiFi with jitter)
Sonos Buffer → Playback:       ~2-3 seconds (Sonos internal)
                               ─────────────
Total perceived latency:       ~3 seconds
```

The 2-3 second delay is Sonos's internal buffering - unavoidable but consistent. The jitter buffer adds ~500ms but eliminates audio skips caused by WiFi latency variations. Once playing, audio is continuous with no dropouts.

---

## Complete Code Path

```
cli.py: stream()
    │
    ▼
streaming.py: TurnTablerStreamer.run()
    ├── setup_audio_source("usb")
    │       └── audio_source.py: USBAudioSource()
    │               └── usb_audio_capture.py: USBAudioCapture()
    │                       └── alsaaudio.PCM()
    │
    ├── setup_streaming_server()
    │       └── streaming_wav.py: WAVStreamingServer()
    │
    ├── start_http_server_background()
    │       └── uvicorn.Server.run() [thread]
    │
    ├── start_producer()
    │       └── _producer_loop() [thread] → fills buffer
    │
    ├── prefill_buffer()
    │       └── waits for ~500ms of audio in buffer
    │
    ├── setup_sonos()
    │       └── soco.SoCo() → group.coordinator
    │
    ├── start_streaming()
    │       └── coordinator.play_uri()
    │
    └── monitor_streaming()
            └── [wait for Ctrl+C]
```
