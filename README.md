# TurnTabler

**Stream vinyl records to Sonos speakers with lossless audio quality.**

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)

Capture analog audio from a turntable and stream it to Sonos speakers via USB audio interface. Uses WAV streaming with infinite headers over native Sonos protocol for true lossless delivery (not AirPlay's lossy AAC-LC).

---

## Installation

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libasound2-dev
```

### Python Package

Requires Python 3.13+ and `uv` package manager:

```bash
git clone https://github.com/yourusername/turntabler
cd turntabler
uv venv && source .venv/bin/activate
uv pip install -e .
```

---

## CLI Usage

TurnTabler provides a simple CLI for streaming and testing.

### Main Commands

```bash
# Stream from USB to auto-discovered Sonos
turntabler stream

# Specify Sonos speaker IP
turntabler stream --sonos-ip 192.168.1.100

# Test with synthetic audio (no hardware needed)
turntabler stream --synthetic

# Quick connectivity test (~30s)
turntabler test quick

# Full validation test (~10 minutes)
turntabler test full

# List available USB audio devices
turntabler list
```

### Examples

```bash
# Stream from USB with custom Sonos speaker
turntabler stream --sonos-ip 192.168.86.63

# Stream from WAV file for testing
turntabler stream --file tests/fixtures/test-loop.wav

# Run extended stability test (30 minutes)
turntabler test full --duration 1800
```

---

## How It Works

```
Turntable (Analog)
    ↓
USB Audio Interface (ALSA capture)
    ↓
TurnTabler (WAV stream server)
    ↓
HTTP GET /stream.wav
    ↓
Sonos Speaker (Native protocol)
    ↓
Lossless playback (48kHz/16-bit PCM)
```

**Key innovation:** WAV with infinite header (`data_size=0xFFFFFFFF`) signals continuous stream to Sonos, enabling lossless playback without special protocols.

**Critical:** When Sonos devices are grouped (e.g., Beam + Sub), commands route to group coordinator automatically. See `CLAUDE.md` for details.

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete architecture, design decisions, project instructions
- **[docs/hardware/usb-audio-interface-guide.md](docs/hardware/usb-audio-interface-guide.md)** - USB hardware research and selection
- **[docs/hardware/USB-HARDWARE-TESTING.md](docs/hardware/USB-HARDWARE-TESTING.md)** - Hardware testing guide
- **[docs/implementation/COMPLETE-ARCHITECTURE.md](docs/implementation/COMPLETE-ARCHITECTURE.md)** - Detailed system design

---

## Development

### Setup

```bash
# Install dependencies (use uv add, NOT uv pip install)
uv add <package>

# Run tests
turntabler test quick    # 30s validation
turntabler test full     # 10min validation

# Lint
uvx ruff check
```

### Key Rules

- **Dependencies:** Always use `uv add <package>` (updates pyproject.toml)
- **Never:** `uv pip install <package>` (missing from pyproject.toml)
- **Except:** `uv pip install -e .` is correct for editable package install

---

## Hardware

**Tested & Recommended:** Behringer UCA222 (~$30-40)
- 16-bit/48kHz (matches Sonos maximum)
- Proven Linux/ALSA compatibility
- Budget-friendly alternative to proprietary solutions

Full hardware guide in `docs/hardware/usb-audio-interface-guide.md`

---

## Status

- ✅ WAV streaming server (production-ready)
- ✅ Sonos control via SoCo with group support
- ✅ CLI application (Typer-based)
- ✅ End-to-end test suite
- ✅ USB device detection (code ready for hardware)

---

**Built to stream vinyl with true lossless quality. No vendor lock-in. No compromises. 🎵**
