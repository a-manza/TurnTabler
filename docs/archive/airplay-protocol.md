# AirPlay Protocol Overview

## AirPlay Versions

### AirPlay 1
- **Released:** 2010 (originally "AirTunes")
- **Transport:** Primarily TCP
- **Audio codec:** ALAC (Apple Lossless)
- **Max quality:** 16-bit/44.1kHz (CD quality)
- **Features:** Audio only, one device at a time

### AirPlay 2
- **Released:** 2018
- **Transport:** UDP + some TCP
- **Audio codec:** ALAC (Apple Lossless)
- **Max quality:** 24-bit/48kHz
- **Features:**
  - Multi-room audio (sync multiple speakers)
  - Buffering improvements (lower latency)
  - Better network resilience
  - HomeKit integration

## RAOP (Remote Audio Output Protocol)

### Overview
RAOP is the underlying protocol for AirPlay audio streaming. It was reverse-engineered by the open-source community.

### Service Discovery (mDNS)
**Service Type:** `_raop._tcp.local.`

**Example record:**
```
Name: Sonos Beam._raop._tcp.local.
IP: 192.168.1.100
Port: 7000
TXT records:
  - am=SonosBeam
  - ch=2 (stereo)
  - cn=0,1 (codecs)
  - et=0,1 (encryption types)
  - sv=false (password required)
  - tp=UDP (transport protocol)
  - vn=3 (version)
```

### Connection Flow

1. **Discovery**
   - Client broadcasts mDNS query for `_raop._tcp.local.`
   - Receivers respond with connection details

2. **Connection Setup**
   - Client connects to receiver's advertised port
   - RTSP protocol handshake (similar to HTTP)
   - Negotiate codec, encryption, timing

3. **Audio Streaming**
   - Audio encoded to ALAC
   - Packetized and sent via UDP (AirPlay 2) or TCP (AirPlay 1)
   - Timing packets keep audio synchronized
   - Control packets handle volume, metadata

4. **Teardown**
   - RTSP TEARDOWN request
   - Connection closed gracefully

## ALAC Codec (Apple Lossless Audio Codec)

### Characteristics
- **Type:** Lossless compression (like FLAC)
- **Compression ratio:** ~40-60% of original size
- **Quality:** Bit-perfect audio (no data loss)
- **Supported formats:**
  - 16-bit, 20-bit, 24-bit, 32-bit
  - Sample rates: 8kHz to 384kHz (practical: 44.1kHz, 48kHz, 96kHz)
  - Mono, stereo, multi-channel

### AirPlay 2 Limitations
While ALAC supports high resolutions, **AirPlay 2 limits transmission to 24-bit/48kHz**

**Why this matters for vinyl:**
- Vinyl typically captured at 24-bit/96kHz or 24-bit/192kHz
- AirPlay will downsample to 24-bit/48kHz
- Still better than CD quality (16-bit/44.1kHz)
- More than sufficient for most vinyl setups

### ALAC in Practice
**Encoding:**
```bash
# FFmpeg example
ffmpeg -i input.wav -c:a alac output.m4a
```

**Streaming:**
- Native tools (VLC, GStreamer) handle ALAC encoding automatically
- No manual codec configuration needed for RAOP output

## Network Requirements

### Bandwidth
**For 24-bit/48kHz stereo:**
- Uncompressed: ~2.3 Mbps
- ALAC compressed: ~1-1.5 Mbps (varies with content)
- **Required:** Stable 2+ Mbps connection

**Most WiFi networks handle this easily**, but Ethernet preferred for:
- Lower latency
- More consistent quality
- Less jitter

### Latency
**Typical AirPlay 2 latency:** 200-300ms

**Breakdown:**
- Encoding: 20-50ms
- Network transmission: 10-50ms
- Buffering: 150-200ms (for smooth playback)

**For turntable streaming:** This latency is imperceptible (you're not interacting)

### Ports
- **mDNS discovery:** UDP 5353
- **RAOP streaming:** Variable (usually 5000-7000 range)
- **Firewall:** May need to allow UDP 6002 for PipeWire RAOP

## Sonos-Specific Considerations

### AirPlay 2 Support
**Sonos speakers with AirPlay 2:**
- Sonos Beam (Gen 1 and 2)
- Sonos Arc
- Sonos One (SL)
- Sonos Five
- Sonos Move, Roam, Era series

**No AirPlay 2:**
- Play:1, Play:3, Play:5 (Gen 1)
- Connect, Connect:Amp (Gen 1)

### Sonos Network Behavior
- Sonos devices advertise themselves via mDNS
- Service name usually includes "Sonos" in device name
- Supports standard RAOP protocol (no proprietary extensions)

### Multi-Room with Sonos
- AirPlay 2 can stream to multiple Sonos speakers simultaneously
- Handled by grouping in Sonos app or AirPlay 2 protocol
- TurnTabler can potentially support this (select multiple devices)

## Audio Quality Validation

### How to Verify Lossless
1. **Check codec:** Ensure ALAC encoding (not AAC/MP3)
2. **Inspect stream:** Use Wireshark to verify RAOP packets
3. **Measure file sizes:** ALAC should be ~50% of WAV size
4. **Spectral analysis:** Compare source vs output (no high-frequency rolloff)

### Quality Checklist for TurnTabler
- [ ] ALAC codec confirmed
- [ ] 24-bit depth maintained (if source is 24-bit)
- [ ] 48kHz sample rate achieved
- [ ] No audible artifacts (clicks, pops, compression)
- [ ] Stereo imaging preserved
- [ ] Dynamic range intact

## Implementation Tools

### Linux RAOP Senders

| Tool | Protocol | Quality | Python Control | Notes |
|------|----------|---------|----------------|-------|
| VLC | RAOP | ALAC | Subprocess/bindings | Proven, simple |
| GStreamer | RAOP | ALAC | Python bindings | Professional-grade |
| PipeWire | RAOP | ALAC | pulsectl | System integration |
| FFmpeg | RAOP | ALAC | Subprocess | Excellent codec support |

### Python Libraries
- **zeroconf:** mDNS discovery for finding AirPlay devices
- **pulsectl:** Control PulseAudio/PipeWire (for RAOP module approach)
- **python-vlc:** VLC bindings (if using VLC backend)
- **PyGObject:** GStreamer bindings (if using GStreamer backend)

## Security Considerations

### Authentication
- AirPlay 1: Optional password (rarely used)
- AirPlay 2: Device pairing (can often be disabled)

**For TurnTabler:**
- Sonos typically doesn't require auth on local network
- Can implement password support if needed (RAOP supports it)

### Encryption
- AirPlay can use encryption for audio stream
- Typically optional on trusted networks
- May add slight latency overhead

**Recommendation:** Start without encryption, add if needed

## References & Further Reading

- [AirPlay 2 Protocol Analysis](https://emanuelecozzi.net/docs/airplay2)
- [ALAC Codec Specification](https://github.com/macosforge/alac)
- [shairport-sync](https://github.com/mikebrady/shairport-sync) - Receiver implementation (good protocol reference)
- [PipeWire RAOP Module](https://docs.pipewire.org/page_module_raop_sink.html)
- [RFC 2326: RTSP](https://tools.ietf.org/html/rfc2326) - Real Time Streaming Protocol (basis for RAOP)
