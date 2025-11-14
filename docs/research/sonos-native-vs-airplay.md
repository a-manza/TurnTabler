# Sonos Native Protocol vs AirPlay Quality Analysis

## Critical Discovery

**Date:** 2025-11-14

### The Quality Problem with AirPlay to Sonos

While researching streaming solutions, we discovered a **critical quality difference** between using AirPlay vs Sonos's native protocol:

**AirPlay to Sonos:**
- Codec delivered: **AAC-LC (LOSSY)**
- AirPlay "strips back" audio quality when streaming to Sonos
- Even though AirPlay 2 protocol theoretically supports lossless ALAC
- Even though devices support 24-bit/48kHz
- **Result: Compressed, lossy audio**

**Sonos Native Protocol:**
- Codec: **FLAC 24-bit, ALAC 24-bit, WAV 16-bit (LOSSLESS)**
- Protocol: UPnP/SOAP
- Same quality as Sonos app native integration
- **Result: TRUE lossless audio**

### Evidence

**Source:** Multiple Sonos Community forum posts and user reports

Key quotes:
- "AirPlay doesn't support lossless on Sonos"
- "AirPlay uses AAC-LC when sending audio to any AirPlay compatible speaker, including Sonos"
- "For lossless audio on Sonos, you must do so from within the Sonos app"
- "Airplay will strip back the song quality, as only certain bitrates are supported"

### Why This Matters for TurnTabler

Our goal is **lossless audio** from turntable to Sonos. Using AirPlay defeats this purpose.

**Original plan (AirPlay via OwnTone):**
```
Turntable → USB (24-bit) → OwnTone (16-bit ALAC) → AirPlay → Sonos (AAC-LC lossy)
                                                                    ^^^^^^^^^^^^
                                                                    NOT LOSSLESS!
```

**Better approach (Sonos native):**
```
Turntable → USB (24-bit) → HTTP Server (FLAC) → Sonos Native → Sonos (FLAC lossless)
                                                                       ^^^^^^^^^^^^^
                                                                       LOSSLESS!
```

---

## Sonos Audio Format Support

### Officially Supported Formats

**From Sonos documentation:**
- **FLAC:** Up to 24-bit (lossless)
- **ALAC:** Up to 24-bit (lossless)
- **WAV:** 16-bit (uncompressed)
- **AIFF:** 16-bit (uncompressed)

### Sample Rate Limitations

**Maximum:** 48 kHz

**Supported rates:**
- 16 kHz
- 22.05 kHz
- 24 kHz
- 32 kHz
- 44.1 kHz
- 48 kHz

**NOT supported:**
- 88.2 kHz
- 96 kHz
- 192 kHz

### Bit Depth Reality Check

**Official:** Sonos supports 24-bit FLAC and ALAC

**Reality:** Some users report that 24-bit content may be truncated to 16-bit internally

**Implication:** Even if truncated, 16-bit FLAC is still **lossless** and better than AAC-LC lossy codec from AirPlay

---

## Sonos Native Streaming Protocol

### UPnP/DLNA

Sonos uses the **Universal Plug and Play (UPnP)** protocol for device control and content streaming.

**Key characteristics:**
- SOAP-based messaging
- HTTP for content delivery
- mDNS for device discovery
- Industry standard (not proprietary)

### How It Works

1. **Discovery:** Sonos devices advertise themselves via UPnP/mDNS
2. **Control:** Send UPnP commands via SOAP/HTTP
3. **Content:** Sonos fetches audio from provided HTTP URI
4. **Playback:** Native decoding of FLAC/ALAC/WAV

### Python Integration: SoCo

**Library:** SoCo (Sonos Controller)
- PyPI package: `soco`
- GitHub: https://github.com/SoCo/SoCo
- Documentation: https://docs.python-soco.com/

**Maturity:**
- 10+ years active development
- 1,300+ GitHub stars
- Python 3.6+ (compatible with 3.13)
- Excellent documentation

**Basic usage:**
```python
from soco import SoCo

# Connect to Sonos device
sonos = SoCo('192.168.1.100')

# Play audio from HTTP URI
sonos.play_uri('http://myserver:8000/audio.flac',
               title='Turntable',
               force_radio=True)  # For live streams
```

---

## Streaming Approaches Comparison

### Approach 1: AirPlay (OwnTone)

**Architecture:**
```
Audio Source → OwnTone Server → AirPlay Protocol → Sonos
```

**Pros:**
- Purpose-built for turntable streaming
- Auto-detection of pipe input
- Mature, proven solution
- Multi-room AirPlay 2 support

**Cons:**
- ❌ **AAC-LC lossy codec to Sonos**
- Heavy (full server)
- 16-bit maximum (pipe input limitation)
- Complex setup

**Audio quality:** Lossy (AAC-LC)

---

### Approach 2: Sonos Native (SoCo + HTTP)

**Architecture:**
```
Audio Source → HTTP Server (FLAC) → Sonos Native Protocol → Sonos
```

**Pros:**
- ✅ **FLAC lossless codec to Sonos**
- Simpler architecture (no full server)
- Pure Python (SoCo library)
- Direct UPnP control
- Potential 24-bit support

**Cons:**
- Must implement HTTP streaming server
- Real-time FLAC encoding required
- Sonos must reach HTTP server on network
- Not as "turnkey" as OwnTone

**Audio quality:** Lossless (FLAC)

---

## HTTP Streaming for Sonos

### Requirements

To stream to Sonos via native protocol:

1. **HTTP Server** hosting audio content
2. **Accessible URI** Sonos can reach
3. **Supported format:** FLAC, ALAC, WAV, MP3, etc.
4. **Proper MIME type:** `audio/flac`, `audio/x-flac`

### Implementation Options

**Option 1: Static File Server**
- Simple HTTP server serving pre-recorded files
- Use Python's `http.server` or Flask
- Good for testing, not for live streams

**Option 2: Real-Time Streaming (Flask/FastAPI)**
```python
from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route('/turntable.flac')
def stream():
    def generate():
        proc = subprocess.Popen(
            ['arecord', '-D', 'hw:1,0', '-f', 'S24_LE',
             '-r', '48000', '-c', '2', '-t', 'flac'],
            stdout=subprocess.PIPE
        )
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk

    return Response(generate(), mimetype='audio/flac')
```

**Option 3: Icecast Server**
- Professional streaming server
- Mature, designed for live audio
- Supports multiple listeners
- More complex setup

---

## Quality Testing Methodology

### How to Verify Codec

**Method 1: Wireshark**
```bash
# Capture network traffic
sudo tcpdump -i any -w sonos-stream.pcap 'host 192.168.86.63'

# Analyze with Wireshark
# Look for HTTP content-type headers
# Inspect audio stream packets
```

**Method 2: Sonos Network Activity**
- Use Sonos app diagnostics
- Check what format Sonos reports receiving
- Monitor network bandwidth (FLAC ~1Mbps, AAC ~256kbps)

**Method 3: Subjective Listening**
- A/B test: Direct Sonos app vs streaming solution
- Listen for compression artifacts
- Compare dynamic range

---

## Bandwidth Requirements

### Lossless Formats

**FLAC 16-bit/44.1kHz:**
- Uncompressed: ~1.4 Mbps
- FLAC compressed: ~700-900 Kbps
- Varies with content complexity

**FLAC 24-bit/48kHz:**
- Uncompressed: ~2.3 Mbps
- FLAC compressed: ~1.2-1.5 Mbps

**WAV 16-bit/44.1kHz:**
- Uncompressed: ~1.4 Mbps
- No compression

### Lossy Formats (for comparison)

**AAC-LC 256 Kbps (AirPlay):**
- Fixed bitrate: 256 Kbps
- Lossy compression

**Network recommendation:**
- Wired Ethernet preferred
- WiFi 802.11n minimum
- Stable connection more important than speed

---

## Latency Considerations

### Expected Latency

**AirPlay:**
- Typical: 200-300 ms
- Buffering for smooth playback

**Sonos Native (HTTP streaming):**
- Unknown - needs testing
- Depends on buffering configuration
- HTTP chunked transfer encoding may add latency

**Turntable use case:**
- Latency < 1 second is acceptable
- Not interactive playback
- Listener doesn't notice delay

---

## Recommendations

### For Lossless Quality: Use Sonos Native Protocol

**Reasoning:**
1. Only way to get true lossless to Sonos
2. AirPlay delivers lossy AAC-LC, defeating our purpose
3. SoCo library is mature and well-documented
4. Python-native integration

### Implementation Strategy

**Phase 1: Validate Approach**
1. Test SoCo library with Sonos Beam
2. Build simple HTTP server streaming FLAC
3. Verify Sonos can play the stream
4. Measure quality and latency

**Phase 2: Real-Time Streaming**
1. Capture USB audio
2. Encode to FLAC in real-time
3. Stream via HTTP
4. Test end-to-end quality

**Phase 3: Production Deployment**
1. Auto-start streaming
2. Error handling
3. Raspberry Pi deployment

### Fallback Position

**If Sonos native streaming proves problematic:**
- High latency
- Unstable streams
- Complexity too great

**Then:** Fall back to OwnTone/AirPlay approach
- Accept AAC-LC lossy quality
- Benefit from turnkey solution

---

## Open Questions (Need Testing)

1. **What quality does Sonos actually receive?**
   - Use Wireshark to verify FLAC codec
   - Check if 24-bit preserved or truncated to 16-bit

2. **What is real-time streaming latency?**
   - Measure turntable → Sonos delay
   - Acceptable threshold: < 1 second

3. **How stable is HTTP streaming?**
   - Test long-duration playback (hours)
   - Network interruption recovery
   - Buffer underrun handling

4. **Does real-time FLAC encoding work?**
   - Can we encode 24-bit/48kHz FLAC fast enough?
   - CPU usage on Raspberry Pi
   - Compression level trade-offs

5. **How does it compare to AirPlay?**
   - A/B listening test
   - If no audible difference, simpler solution wins
   - Document findings

---

## References

- [Sonos Community: AirPlay vs Native Lossless](https://en.community.sonos.com/controllers-and-music-services-229131/apple-music-lossless-via-airplay-vs-native-integration-6926101)
- [Sonos Supported Audio Formats](https://support.sonos.com/en-us/article/supported-audio-formats-for-sonos-music-library)
- [SoCo Documentation](https://docs.python-soco.com/)
- [Sonos UPnP API (unofficial)](https://en.community.sonos.com/advanced-setups-229000/sonos-api-6858805)
