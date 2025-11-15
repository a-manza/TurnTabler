# AirPlay Sender vs Receiver Architecture

## The Critical Distinction

### Receiver (Server/Sink)
An AirPlay **receiver** accepts incoming AirPlay streams from other devices.

**Examples:**
- Sonos Beam (built-in AirPlay 2)
- Apple TV
- HomePod
- **Linux software:** shairport-sync, RPiPlay, UxPlay

**Use case:** Make your Linux/Pi appear as an AirPlay speaker that iOS/Mac can stream TO.

### Sender (Client/Source)
An AirPlay **sender** transmits audio TO AirPlay receivers.

**Examples:**
- iPhone, iPad, Mac (built-in)
- iTunes/Music app
- **What we need:** Linux/Pi that sends audio TO Sonos

## Why This Matters for TurnTabler

### The Problem
Most Linux AirPlay tutorials focus on making Linux a **receiver**:
- "Turn your Raspberry Pi into an AirPlay speaker!"
- "Stream from iPhone to Linux"
- shairport-sync: "AirPlay audio player" (receiver)

### Our Requirement
```
Turntable → Linux/Pi → [SENDER] → Sonos Beam
                       ^^^^^^^^
                    This is what we need!
```

The Sonos Beam is already an AirPlay receiver. We need Linux to be a sender.

## Available Sender Solutions for Linux

### 1. PipeWire/PulseAudio RAOP Module
**Module:** `module-raop-sink` (PipeWire) or `module-raop-discover` (PulseAudio)

**How it works:**
- Discovers AirPlay receivers on network
- Creates audio sinks that send to those receivers
- Routes system audio to AirPlay devices

**Status:** Available, well-tested

### 2. VLC
**Capability:** `--sout` (stream output) with RAOP protocol

**Command example:**
```bash
cvlc audio.mp3 --sout '#raop{host=192.168.1.100}' --no-sout-video
```

**Status:** Proven, simple to use

### 3. GStreamer
**Plugin:** `raopsink`

**Pipeline example:**
```bash
gst-launch-1.0 filesrc location=audio.flac ! decodebin ! raopsink host=192.168.1.100
```

**Status:** Professional-grade, flexible

### 4. FFmpeg
**Output format:** RAOP via network protocol

**Status:** Codec support excellent, RAOP output needs verification

### 5. OwnTone (forked-daapd)
**Type:** Full music server with AirPlay sender capability

**Approach:** Complete solution, includes line-in capture

**Status:** Feature-rich but heavyweight for our needs

## Protocol: RAOP (Remote Audio Output Protocol)

### What is RAOP?
- Apple's proprietary protocol for AirPlay audio
- Streams audio over network (UDP for AirPlay 2, TCP for AirPlay 1)
- Uses ALAC (Apple Lossless Audio Codec) for compression

### Service Discovery
- Uses mDNS/Bonjour for device discovery
- Service type: `_raop._tcp.local.`
- Provides device name, IP, port, capabilities

### Authentication
- AirPlay 1: Optional password
- AirPlay 2: Device verification (can be disabled)

## Implementation Implications

### For TurnTabler
We need to:
1. **Discover** AirPlay receivers (Sonos Beam) via mDNS
2. **Encode** audio to ALAC format
3. **Transmit** via RAOP protocol to receiver
4. **Control** this process programmatically from Python

### Architecture Options

**Option A: Use native tools (VLC/GStreamer)**
```
Python → Control native tool → RAOP sender → Sonos
```
- Pro: Proven, reliable, high quality
- Pro: Don't reinvent the wheel
- Con: External dependency

**Option B: Pure Python RAOP implementation**
```
Python → Custom RAOP client → Sonos
```
- Pro: Full control, portable
- Con: Complex protocol, potential quality issues
- Con: Maintenance burden

**Decision:** Use native tools, control from Python (Option A)

## Key Takeaways

1. **Don't use shairport-sync** - It's a receiver, not a sender
2. **RAOP modules exist** - PipeWire, VLC, GStreamer all support sending
3. **mDNS discovery** - Use `_raop._tcp.local.` to find Sonos Beam
4. **ALAC codec** - This is how we achieve lossless quality
5. **Python orchestration** - We control native tools, not implement RAOP ourselves

## References
- [shairport-sync GitHub](https://github.com/mikebrady/shairport-sync) - Receiver implementation
- [PipeWire RAOP Sink](https://docs.pipewire.org/page_module_raop_sink.html)
- AirPlay protocol reverse engineering (various sources)
