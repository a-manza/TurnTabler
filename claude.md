# TurnTabler Project

## Vision
Bypass Sonos vendor lock-in to enable streaming vinyl records from a turntable to Sonos speakers with lossless audio quality. Build an open-source, Python-driven solution that runs on Linux (development) and Raspberry Pi 5 (production).

## The Problem
Sonos doesn't provide a simple way to stream analog audio (like vinyl records) to their speaker systems without purchasing expensive, proprietary hardware. We want to use AirPlay 2 (which Sonos Beam supports) to stream lossless audio from a turntable via a Raspberry Pi.

## Project Goals
1. **Prove the concept** on existing Linux machine before investing in Pi hardware
2. **Lossless audio quality** - preserve vinyl fidelity (24-bit/48kHz if possible)
3. **Python-driven** - orchestrate with Python, leverage native tools for quality/reliability
4. **Modular design** - easy to evolve from file streaming → system audio → USB input
5. **Pi-portable** - same codebase runs on Ubuntu and Raspberry Pi OS
6. **Programmatic control** - CLI interface, potential for future automation/UI

## Critical Technical Understanding

### AirPlay Sender vs Receiver
**THE KEY INSIGHT:** Most Linux AirPlay software (shairport-sync, RPiPlay, UxPlay) makes the device an AirPlay **receiver**. Your Sonos Beam is already a receiver. We need Linux/Pi to be an AirPlay **sender/transmitter**.

### Audio Quality Requirements
- **Codec:** ALAC (Apple Lossless Audio Codec) - lossless compression
- **Target:** 24-bit/48kHz (maximum AirPlay 2 supports)
- **Source:** Vinyl via USB audio interface (future phase)
- **Latency:** ~200-300ms expected (acceptable for vinyl playback)

## Architecture

### Current (Phase 1): File Streaming POC
```
Audio File (FLAC/WAV) →
Python Orchestration →
Native Tool (VLC/GStreamer/FFmpeg) →
RAOP Protocol (ALAC encoding) →
Network (WiFi/Ethernet) →
Sonos Beam (AirPlay 2 receiver)
```

### Future (Phase 4): Turntable Streaming
```
Turntable (Analog Audio) →
USB Audio Interface (Behringer UCA202 or HiFiBerry DAC+ ADC) →
Raspberry Pi 5 (ALSA capture) →
Python Orchestration →
Native Streaming Tool →
RAOP/AirPlay 2 →
Sonos Beam
```

## Technology Stack

### Core Language & Tooling
- **Python 3.13** - Modern Python with latest features
- **uv** - Fast, modern Python package manager (only package manager used)
- **Click** - CLI framework for user interface

### Audio Streaming Backend (TBD - Task 1)
Options under evaluation:
1. **VLC** - Proven RAOP support, simple subprocess control
2. **GStreamer** - Professional pipeline, Python bindings available
3. **PipeWire/PulseAudio** - System audio server with RAOP modules
4. **FFmpeg** - Versatile codec support, subprocess control

Decision criteria: quality, reliability, Pi portability, Python integration ease

### Device Discovery
- **zeroconf** - mDNS/Bonjour for finding AirPlay devices on network
- Search for `_raop._tcp.local.` services

## Module Structure

```
src/turntabler/
  __init__.py           # Package initialization
  discovery.py          # mDNS AirPlay device discovery
  streaming.py          # Core streaming abstraction
  backends/             # Pluggable streaming backends
    __init__.py
    vlc.py             # VLC-based implementation
    gstreamer.py       # GStreamer implementation (future)
    pipewire.py        # PipeWire/PulseAudio (future)
  audio.py              # Audio source handling
  cli.py                # Click-based CLI
  config.py             # User settings, device memory

docs/                   # Structured knowledge base
  research/            # Technical research findings
  linux-setup/         # System configuration guides
  hardware/            # Hardware specifications
  implementation/      # Decision logs, results

pyproject.toml          # uv-managed dependencies
README.md               # User-facing documentation
```

## Design Principles

### Modularity
- **Pluggable backends:** Easy to swap VLC ↔ GStreamer ↔ PipeWire
- **Abstract audio sources:** File → System Audio → USB Input
- **Device abstraction:** Support multiple Sonos devices, other AirPlay receivers

### Simplicity First
- Start with simplest working implementation (likely VLC subprocess)
- Add complexity only when needed
- Prefer battle-tested tools over custom implementations

### Documentation Driven
- Capture all research and decisions in `/docs`
- `claude.md` as living project knowledge base
- Never repeat foundational research

## Evolution Roadmap

### Phase 1: Proof of Concept (Current)
- **Goal:** Stream lossless audio files from Linux to Sonos Beam
- **Success:** Proven tech stack, documented quality, modular code
- **Deliverables:** Working CLI, tech stack decision, quality report

### Phase 2: System Audio Streaming
- Route any Linux audio to Sonos
- Useful for Spotify, YouTube, browser audio

### Phase 3: Raspberry Pi Deployment
- Deploy same codebase to Pi 5
- Verify identical quality/performance
- Create systemd service for auto-start

### Phase 4: USB Audio Integration
- Add USB audio interface (Behringer UCA202 or HiFiBerry)
- Capture analog audio from turntable
- Real-time streaming to Sonos

### Phase 5: Production Features
- Web UI for control
- Multi-room support (multiple Sonos devices)
- Monitoring dashboard
- Volume control, basic EQ

## Hardware Plan (Post-POC)

### Raspberry Pi 5 Setup
- **Model:** 4GB or 8GB RAM
- **Storage:** 32GB+ microSD (Class 10/A2)
- **Power:** Official 5V/5A USB-C PD supply
- **Cooling:** Active cooling recommended
- **Network:** Ethernet preferred (lower latency than WiFi)

### USB Audio Interface Options
1. **Budget:** Behringer UCA202 ($30-40) - 16-bit/48kHz, RCA inputs
2. **Best:** HiFiBerry DAC+ ADC Pro ($65) - 24-bit/192kHz, HAT form factor, I2S

### Estimated Total Cost
- Raspberry Pi 5 (4GB): $60
- USB Audio Interface: $35-65
- Power supply, case, SD card: ~$40
- **Total: $135-165**

## Current Status

**Phase:** 1 - Proof of Concept
**Next Task:** Create research documentation and evaluate tech stack options
**Blockers:** None

## Key Decisions Log

### 2025-11-12: Project Initialization
- **Decision:** Python-driven architecture (not pure Python)
- **Rationale:** Leverage battle-tested native tools (VLC/GStreamer) via Python orchestration for maximum quality and reliability
- **Impact:** Faster development, higher quality, easier Pi portability

### 2025-11-12: Package Management
- **Decision:** Use uv exclusively for Python package management
- **Rationale:** Modern, fast, aligns with Python 3.13 best practices
- **Impact:** Simpler dependency management

### Tech Stack Selection
- **Status:** Pending evaluation (Task 1)
- **Leading candidate:** VLC (proven in research, simple integration)
- **Evaluation criteria:** Quality, latency, Python control ease, Pi portability

## Resources

### External Documentation
- [Raspberry Pi 5 AirPlay Guide](docs/hardware/raspberry-pi-5-guide.md) - Comprehensive setup guide
- [AirPlay Protocol Specs](docs/research/airplay-protocol.md)
- [Tech Stack Decision](docs/implementation/tech-stack-decision.md) (pending)

### Related Projects
- shairport-sync - AirPlay receiver (not sender, but good reference)
- philippe44/AirConnect - Bridges UPnP/Sonos to AirPlay
- OwnTone - Full-featured music server with AirPlay support

## Notes & Learnings

### Critical Pitfall Avoided
Initially considered shairport-sync, but this is a **receiver** not a **sender**. The Raspberry Pi guide document clarified this fundamental architecture requirement.

### Quality Insights
- AirPlay 2 max quality: 24-bit/48kHz (sufficient for vinyl)
- ALAC codec is truly lossless (bit-perfect preservation)
- Expected latency: 200-300ms (not noticeable for music playback)
- Network quality matters - Ethernet > WiFi for consistency
