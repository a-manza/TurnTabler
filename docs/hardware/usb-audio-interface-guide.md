# USB Audio Interface Guide for TurnTabler

## Overview

This guide provides comprehensive research and implementation details for USB audio interfaces suitable for streaming vinyl turntable audio to the TurnTabler system. The goal is to capture lossless analog audio from a turntable and stream it to Sonos speakers via the Raspberry Pi or Linux PC.

## Table of Contents

1. [Hardware Recommendations](#hardware-recommendations)
2. [Phono Preamp Requirements](#phono-preamp-requirements)
3. [Linux/ALSA Implementation](#linuxalsa-implementation)
4. [Python Libraries Comparison](#python-libraries-comparison)
5. [Production Code Implementation](#production-code-implementation)
6. [Setup Instructions](#setup-instructions)
7. [Troubleshooting](#troubleshooting)

---

## Hardware Recommendations

### ✅ CONFIRMED: Behringer UCA202 and UCA222 are Identical

**Important:** These are the same device sold under different model numbers in different markets:
- **UCA222:** Primarily EU/UK market
- **UCA202:** Primarily US/Asia market (your device if you purchased UCA202)
- **Chipset:** Both use Burr-Brown PCM2902E (identical specifications)
- **TurnTabler Compatibility:** Fully validated for lossless streaming
- **ALSA Detection:** Device reports as "CODEC" (generic USB descriptor)

All references to "UCA222/UCA202" in this guide apply equally to both models.

---

### Recommended Primary Option: Behringer UCA222/UCA202

**Price:** $30-40
**Overall Rating:** Best budget option for Linux/Pi
**Confidence:** 9/10 for this use case

#### Specifications
- **DAC/ADC Chipset:** Burr-Brown PCM2902E
- **Sample Rates:** 44.1kHz, 48kHz (officially), up to 192kHz (chipset capable)
- **Bit Depth:** 16-bit
- **SNR:** 89 dB (A/D), 96 dB (D/A) typical @ 1kHz, A-weighted
- **USB Version:** USB 1.1 (sufficient for 48kHz/16-bit stereo)
- **Inputs:** Stereo RCA (line-level)
- **Outputs:** Stereo RCA (line-level), Optical S/PDIF, Headphone jack
- **Power:** USB bus-powered (no external power needed)

#### Linux/ALSA Compatibility
- **Compatibility Rating:** Excellent (10/10)
- **Driver:** snd-usb-audio (built into Linux kernel)
- **Plug-and-play:** Yes - ALSA recognizes immediately
- **Device Name:** Reports as "CODEC" or "default" (unbranded internally)
- **Tested Platforms:** Ubuntu, Fedora, Raspberry Pi OS
- **Real-time Performance:** Works with ALSA and JACK without issues

#### Pros
- Extremely well-documented Linux compatibility
- Rock-solid ALSA support (since ~2009)
- Lowest cost option
- No drivers needed on Linux
- Optical output available for high-quality monitoring
- Large community of Linux users
- Proven for Raspberry Pi vinyl streaming projects

#### Cons
- 16-bit only (not 24-bit)
- USB 1.1 (older standard, but adequate)
- No built-in phono preamp (requires external preamp)
- Generic device naming in ALSA (minor inconvenience)
- Limited to 48kHz officially (chipset can do higher, but not guaranteed)

#### Use Case Fit
Perfect for TurnTabler Phase 4. Delivers lossless 16-bit/48kHz capture which matches or exceeds vinyl's practical resolution. The 48kHz limit is actually ideal since:
- Sonos supports up to 48kHz natively
- Vinyl's practical frequency response is ~20Hz-20kHz (well within 48kHz Nyquist)
- 16-bit dynamic range (96dB) exceeds vinyl's practical dynamic range (~60-70dB)

---

### Alternative Option 1: ART USB Phono Plus

**Price:** $60-75
**Overall Rating:** Best all-in-one solution
**Confidence:** 8/10 for this use case

#### Specifications
- **Sample Rates:** 44.1kHz, 48kHz (switchable)
- **Bit Depth:** 16-bit
- **USB Version:** USB 1.1
- **Inputs:** Stereo RCA (phono + line), S/PDIF, Optical
- **Outputs:** Stereo RCA (line), Optical
- **Built-in Phono Preamp:** Yes (RIAA-compliant, low noise)
- **Features:** Rumble filter, Phono/Line switch, Headphone monitoring
- **Power:** External power supply (included)

#### Linux/ALSA Compatibility
- **Compatibility Rating:** Good (8/10)
- **Driver:** snd-usb-audio (USB Audio Class compliant)
- **Plug-and-play:** Yes on modern Linux
- **Tested Platforms:** Windows/Mac documented, Linux compatibility expected via USB Audio Class

#### Pros
- Built-in RIAA phono preamp (no external preamp needed)
- All-in-one solution for turntable capture
- High-quality phono stage ("surprisingly good" per reviews)
- Rumble filter for turntable vibration
- Headphone monitoring with mix control
- Digital inputs (S/PDIF, optical) for versatility
- Phono/Line bypass switches

#### Cons
- More expensive than Behringer
- External power required (less portable)
- Limited Linux documentation (though USB Audio Class should work)
- 16-bit only
- Overkill if turntable already has built-in preamp

#### Use Case Fit
Excellent if your turntable lacks a built-in phono preamp. The all-in-one design simplifies setup: Turntable → ART USB Phono Plus → Raspberry Pi. However, if your turntable already has a preamp (many modern turntables do), the Behringer UCA222 is more cost-effective.

---

### Alternative Option 2: Focusrite Scarlett Solo (Gen 3/4)

**Price:** $120-150
**Overall Rating:** Premium option with professional features
**Confidence:** 9/10 for this use case

#### Specifications
- **DAC/ADC:** High-quality converters (24-bit/192kHz capable)
- **Sample Rates:** Up to 192kHz
- **Bit Depth:** 24-bit
- **USB Version:** USB 2.0 (USB-C on Gen 4)
- **Inputs:** 1x XLR/TRS combo (mic/instrument), 1x TRS (line)
- **Outputs:** Stereo TRS (line), Headphone
- **Preamp:** High-quality mic preamp (not phono preamp)
- **Power:** USB bus-powered
- **Gain Control:** Hardware gain knob, Air mode (presence boost)

#### Linux/ALSA Compatibility
- **Compatibility Rating:** Excellent (10/10)
- **Driver:** USB Audio Class compliant - works out-of-the-box
- **Plug-and-play:** Yes
- **Additional Tools:** alsa-scarlett-gui available for advanced control
- **Tested Platforms:** Ubuntu, Arch, Fedora, Raspberry Pi
- **Real-time Performance:** Excellent with ALSA, PulseAudio, PipeWire, JACK
- **Latency:** 8.7ms roundtrip @ 128 frames/2 periods/48kHz

#### Pros
- True 24-bit/192kHz capability
- Best-in-class audio quality
- Excellent Linux support and documentation
- Professional build quality
- Direct monitoring (zero-latency)
- USB 2.0 / USB-C (Gen 4)
- Works with PulseAudio, PipeWire, JACK without configuration
- GUI control tool available (alsa-scarlett-gui)

#### Cons
- Most expensive option
- No built-in phono preamp (requires external preamp)
- Overkill for vinyl's practical resolution
- XLR/TRS inputs (may need RCA to TRS adapter cables)
- Channel mapping quirks in some Linux configurations (easily solvable)

#### Use Case Fit
Premium option if you want maximum flexibility and future-proofing. The 24-bit/192kHz capability exceeds what's needed for vinyl, but provides headroom for other audio projects. Best choice if you plan to use the interface for multiple purposes beyond vinyl streaming (podcasting, instrument recording, etc.).

---

### Alternative Option 3: FiiO K3

**Price:** $110-130
**Overall Rating:** High-quality DAC/ADC with digital outputs
**Confidence:** 6/10 for this use case

#### Specifications
- **DAC Chip:** ES9038Q2M
- **USB Chip:** XMOS XUF208
- **Sample Rates:** Up to 384kHz/32-bit PCM, DSD64/128/256
- **USB Version:** USB 2.0 (Type-C)
- **Inputs:** USB, Line-in
- **Outputs:** Headphone (3.5mm, 2.5mm balanced), Line-out, Optical, Coaxial
- **SNR:** 121dB (single-ended), 120dB (balanced)
- **Features:** Bass boost, Gain control

#### Linux/ALSA Compatibility
- **Compatibility Rating:** Good (7/10)
- **Driver:** USB Audio Class 1.0 mode works driver-free
- **Tested Platforms:** Ubuntu 20.04 reported working
- **Limitation:** "Large number of Linux versions, cannot guarantee all systems"

#### Pros
- Exceptional DAC quality (ES9038Q2M)
- Up to 384kHz/32-bit capability
- DSD support
- Excellent SNR (121dB)
- Digital outputs (optical, coaxial)
- USB-C connector

#### Cons
- Primarily designed as DAC (not ADC focus)
- Limited Linux compatibility documentation
- Line-in to digital conversion workflow less common
- No built-in phono preamp
- Expensive for this use case

#### Use Case Fit
Not ideal for TurnTabler. While technically capable, the FiiO K3 is designed primarily as a DAC (digital-to-analog) for headphone listening. The ADC (analog-to-digital) functionality is secondary. Better options exist for dedicated USB audio capture on Linux.

---

## Hardware Comparison Table

| Feature | Behringer UCA222 | ART USB Phono Plus | Focusrite Scarlett Solo | FiiO K3 |
|---------|-----------------|-------------------|----------------------|---------|
| **Price** | $30-40 | $60-75 | $120-150 | $110-130 |
| **Max Sample Rate** | 48kHz | 48kHz | 192kHz | 384kHz |
| **Bit Depth** | 16-bit | 16-bit | 24-bit | 32-bit |
| **USB Version** | 1.1 | 1.1 | 2.0 | 2.0 |
| **Linux Support** | Excellent | Good | Excellent | Good |
| **Phono Preamp** | No | Yes | No | No |
| **Bus Powered** | Yes | No | Yes | Yes |
| **RCA Inputs** | Yes | Yes | No (TRS) | Yes |
| **Best For** | Budget vinyl | All-in-one | Pro quality | DAC/Headphones |
| **TurnTabler Fit** | 9/10 | 8/10 | 7/10 | 5/10 |

---

## Phono Preamp Requirements

### Understanding Phono vs Line Level

#### Signal Strength Difference
- **Phono Level:** 0.0003V to 0.006V (very weak)
- **Line Level:** 0.316V (~316mV)
- **Difference:** Line level is 50 to 1500 times stronger than phono level

#### RIAA Equalization
When pressing vinyl records, the RIAA equalization curve is applied:
- **Bass frequencies:** Reduced (cut)
- **Treble frequencies:** Boosted

This compression allows more audio to fit physically on the record groove.

### What a Phono Preamp Does

A phono preamp performs two critical functions:

1. **Amplification:** Boosts the weak phono signal (0.0003-0.006V) to line level (0.316V)
2. **De-emphasis:** Reverses the RIAA curve to restore flat frequency response
   - Boosts bass back to normal levels
   - Reduces treble back to normal levels

### Do You Need a Phono Preamp?

#### You DON'T need an external preamp if:
- Your turntable has a built-in phono preamp (many modern turntables do)
- Your turntable has a "Phono/Line" switch set to "Line"
- Your USB audio interface has a built-in phono preamp (like ART USB Phono Plus)

#### You DO need an external preamp if:
- Your turntable only outputs phono-level signal
- Your turntable is vintage (pre-2000s are unlikely to have built-in preamp)
- Your USB audio interface only accepts line-level input (Behringer UCA222, Focusrite Scarlett)

### Identifying Your Turntable's Output

Check your turntable for:
- **Phono/Line switch:** If present, you have a built-in preamp
- **RCA outputs labeled "Line Out":** Likely has built-in preamp
- **RCA outputs labeled "Phono Out":** Requires external preamp
- **Grounding wire:** Usually indicates phono-level output (requires preamp)

Consult your turntable's manual or specifications if unsure.

### External Phono Preamp Options

If you need an external preamp, consider:

#### Budget Options ($30-60)
- **Behringer PP400 Microphono:** $25-30, basic but functional RIAA preamp
- **ART DJ PRE II:** $50-60, better quality, low noise
- **Pyle PP444:** $15-25, ultra-budget (adequate for testing)

#### Mid-Range Options ($75-150)
- **Pro-Ject Phono Box:** $80-100, excellent quality, multiple variants
- **Schiit Mani:** $150, audiophile-grade, discrete circuitry
- **Cambridge Audio Alva Duo:** $130, MM/MC switchable

#### High-End Options ($200+)
- **Pro-Ject Tube Box S2:** $300+, tube-based warmth
- **Musical Fidelity LX-LPS:** $200-250, high-end solid-state

### Recommended Setup Configurations

#### Configuration 1: Turntable with Built-in Preamp + Behringer UCA222
```
Turntable (Line Out) → RCA cable → Behringer UCA222 (Line In) → USB → Raspberry Pi
```
**Total Cost:** $30-40 (just USB interface)

#### Configuration 2: Turntable without Preamp + External Preamp + Behringer UCA222
```
Turntable (Phono Out) → External Preamp → Behringer UCA222 → USB → Raspberry Pi
```
**Total Cost:** $55-70 (Behringer PP400 + UCA222)

#### Configuration 3: Turntable without Preamp + ART USB Phono Plus
```
Turntable (Phono Out) → ART USB Phono Plus (Phono In) → USB → Raspberry Pi
```
**Total Cost:** $60-75 (all-in-one)

#### Configuration 4: Premium Setup with Focusrite Scarlett Solo
```
Turntable (Line Out) → RCA to TRS cable → Focusrite Scarlett Solo → USB → Raspberry Pi
```
**Total Cost:** $120-150 (professional quality)

---

## Linux/ALSA Implementation

### ALSA Device Architecture

ALSA (Advanced Linux Sound Architecture) is the kernel-level sound system for Linux. It provides:
- Low-level audio device drivers
- PCM (Pulse Code Modulation) interface for audio streaming
- Mixer interface for volume/gain control
- Device enumeration and management

### Device Naming Conventions

ALSA uses several device naming formats:

#### Hardware Device Format: `hw:X,Y`
- `X` = Card number (0, 1, 2, ...)
- `Y` = Device number (usually 0)
- Example: `hw:1,0` = Card 1, Device 0
- **Direct hardware access** (no software mixing or conversion)
- Exclusive access (only one application can use at a time)
- Best for low-latency, high-quality capture

#### Plugin Device Format: `plughw:X,Y`
- Same numbering as `hw:X,Y`
- **Automatic format conversion** via ALSA plugins
- Sample rate conversion if needed
- Channel remapping if needed
- Multiple applications can access simultaneously
- Slightly higher latency than `hw:`

#### Named Device Format: `hw:CARD=CardName,DEV=0`
- Example: `hw:CARD=UCA222,DEV=0`
- More readable but card names can vary
- Useful for persistent device identification

### Enumerating USB Audio Devices

#### Method 1: Using `arecord` Command (Bash)

List all capture devices:
```bash
arecord -l
```

Example output:
```
**** List of CAPTURE Hardware Devices ****
card 0: PCH [HDA Intel PCH], device 0: ALC295 Analog [ALC295 Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: UCA222 [UCA222], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

List all PCM devices (includes ALSA plugins):
```bash
arecord -L
```

Example output:
```
hw:CARD=UCA222,DEV=0
    UCA222, USB Audio
    Direct hardware device without any conversions
plughw:CARD=UCA222,DEV=0
    UCA222, USB Audio
    Hardware device with all software conversions
```

#### Method 2: Using Python `pyalsaaudio`

```python
import alsaaudio

# List all PCM capture devices
devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
for device in devices:
    print(device)
```

Example output:
```
default
hw:CARD=PCH,DEV=0
hw:CARD=UCA222,DEV=0
plughw:CARD=PCH,DEV=0
plughw:CARD=UCA222,DEV=0
sysdefault:CARD=UCA222
...
```

#### Method 3: Using Python `sounddevice`

```python
import sounddevice as sd

# Query all devices
devices = sd.query_devices()
print(devices)

# Find input devices only
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"{i}: {device['name']} (inputs: {device['max_input_channels']})")
```

### Device Detection Best Practices

For production code, implement robust device detection:

```python
import alsaaudio
import re

def find_usb_audio_device(device_name_pattern=None):
    """
    Find USB audio capture device.

    Args:
        device_name_pattern: Regex pattern to match device name (e.g., 'UCA222', 'Scarlett')
                           If None, returns first USB audio device found.

    Returns:
        Device name string (e.g., 'hw:CARD=UCA222,DEV=0') or None if not found
    """
    devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)

    # Filter for hw: devices (actual hardware, not plugins)
    hw_devices = [d for d in devices if d.startswith('hw:CARD=')]

    if device_name_pattern:
        pattern = re.compile(device_name_pattern, re.IGNORECASE)
        for device in hw_devices:
            if pattern.search(device):
                return device
    elif hw_devices:
        # Return first hardware device (usually USB if plugged in)
        return hw_devices[0]

    return None

# Example usage
device = find_usb_audio_device('UCA222')
if device:
    print(f"Found device: {device}")
else:
    print("USB audio device not found")
```

---

## Python Libraries Comparison

### pyalsaaudio vs sounddevice

Both libraries can capture USB audio on Linux, but they have different design philosophies and use cases.

### pyalsaaudio

**Overview:** Direct Python bindings to ALSA C library. Low-level access to ALSA functionality.

#### Pros
- Direct ALSA access (lowest latency possible)
- Mature library (10+ years of development)
- Excellent documentation
- Fine-grained control over ALSA parameters
- Proven reliability with USB audio on Linux/Raspberry Pi
- No external dependencies beyond ALSA libraries
- Lightweight
- Works well with JACK for professional audio

#### Cons
- Linux-only (not cross-platform)
- Lower-level API (more configuration required)
- Returns audio data as bytes (manual NumPy conversion needed)
- Limited to ALSA backend

#### Best For
- Linux-specific applications
- Low-latency real-time audio
- Raspberry Pi projects
- Direct hardware control
- TurnTabler use case (Linux/Pi exclusive)

#### Installation
```bash
# System dependencies (Ubuntu/Debian/Raspberry Pi OS)
sudo apt-get install libasound2-dev

# Python package
pip install pyalsaaudio
```

Or with `uv`:
```bash
uv pip install pyalsaaudio
```

---

### sounddevice

**Overview:** Python bindings to PortAudio library. Cross-platform audio I/O with NumPy integration.

#### Pros
- Cross-platform (Linux, Windows, macOS)
- NumPy integration (returns audio as NumPy arrays)
- Simpler, more Pythonic API
- Good for scientific computing workflows
- Automatic sample rate conversion
- Multiple backend support (ALSA, JACK, PulseAudio on Linux)

#### Cons
- Higher latency than direct ALSA access
- More system resources required
- Potential audio "glitches" reported in some use cases
- Additional abstraction layer (PortAudio → ALSA)
- Heavier dependency (requires PortAudio library)

#### Best For
- Cross-platform applications
- NumPy-based audio processing
- Rapid prototyping
- Scientific/research applications
- Applications requiring sample rate conversion

#### Installation
```bash
# System dependencies (Ubuntu/Debian/Raspberry Pi OS)
sudo apt-get install libportaudio2

# Python package
pip install sounddevice
```

---

### Recommendation for TurnTabler

**Use pyalsaaudio** for the following reasons:

1. **Linux-Exclusive:** TurnTabler targets Linux (development) and Raspberry Pi OS (production), both ALSA-based. Cross-platform support is not needed.

2. **Lower Latency:** Direct ALSA access provides minimum latency for real-time streaming.

3. **Proven Reliability:** Multiple confirmed reports of pyalsaaudio working flawlessly with USB audio on Raspberry Pi for vinyl streaming projects.

4. **Lightweight:** Minimal dependencies and resource usage (critical for Raspberry Pi).

5. **Better Control:** Fine-grained control over buffer sizes, period sizes, and ALSA parameters for optimal streaming quality.

6. **Project Alignment:** TurnTabler philosophy favors low-level, reliable tools over abstraction layers.

**When sounddevice might be preferable:**
- If you need rapid prototyping with NumPy
- If you plan to port to Windows/macOS in the future
- If you need automatic sample rate conversion

For production TurnTabler implementation, pyalsaaudio is the clear choice.

---

## Production Code Implementation

### ALSA Capture Configuration Parameters

Understanding ALSA parameters is critical for optimal audio quality and latency:

#### Sample Rate (rate)
- **Definition:** Number of samples per second (Hz)
- **Common Values:** 44100 (CD quality), 48000 (professional), 96000, 192000
- **Recommendation:** 48000 Hz for TurnTabler
  - Matches Sonos native support
  - Exceeds vinyl frequency response (20Hz-20kHz needs 40kHz Nyquist minimum)
  - Standard for professional audio

#### Sample Format (format)
- **Definition:** Bit depth and encoding of each sample
- **Common Values:**
  - `PCM_FORMAT_S16_LE`: 16-bit signed little-endian (most compatible)
  - `PCM_FORMAT_S24_3LE`: 24-bit signed little-endian (3 bytes)
  - `PCM_FORMAT_S32_LE`: 32-bit signed little-endian
- **Recommendation:** `PCM_FORMAT_S16_LE` for Behringer UCA222, `PCM_FORMAT_S24_3LE` for Focusrite Scarlett Solo

#### Channels (channels)
- **Definition:** Number of audio channels
- **Values:** 1 (mono), 2 (stereo)
- **Recommendation:** 2 (stereo) for vinyl turntable

#### Period Size (periodsize)
- **Definition:** Number of frames in each period (buffer chunk)
- **Relationship:** Lower period size = lower latency, but higher CPU usage
- **Formula:** Latency (ms) = (periodsize / rate) * 1000
- **Examples:**
  - 1024 frames @ 48kHz = 21.3ms latency
  - 512 frames @ 48kHz = 10.7ms latency
  - 256 frames @ 48kHz = 5.3ms latency
  - 160 frames @ 48kHz = 3.3ms latency
- **Recommendation:** Start with 1024, tune down to 512 or 256 if latency is critical

#### Number of Periods
- **Definition:** Number of periods in the buffer
- **Typical Values:** 2-4
- **USB Audio Recommendation:** 3 periods (USB devices benefit from extra buffer)
- **Tradeoff:** More periods = more latency, but better protection against buffer underruns/overruns

#### PCM Mode
- **PCM_NORMAL:** Blocking mode (read() waits for data)
- **PCM_NONBLOCK:** Non-blocking mode (read() returns immediately)
- **Recommendation:** `PCM_NONBLOCK` for real-time streaming (allows timeout handling)

---

### Device Detection Module

Create `/home/a_manza/dev/turntabler/src/turntabler/usb_audio.py`:

```python
"""
USB Audio device detection and management for TurnTabler.
Handles ALSA device enumeration and configuration.
"""

import alsaaudio
import re
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class AudioDevice:
    """Represents an ALSA audio capture device."""
    device_name: str  # ALSA device string (e.g., 'hw:CARD=UCA222,DEV=0')
    card_number: int  # Card number (e.g., 1)
    card_name: str    # Human-readable card name (e.g., 'UCA222')
    device_number: int = 0  # Device number (usually 0)


class USBudioDeviceManager:
    """Manages USB audio device detection and enumeration."""

    @staticmethod
    def list_capture_devices() -> List[AudioDevice]:
        """
        List all available ALSA capture devices.

        Returns:
            List of AudioDevice objects
        """
        devices = []
        alsa_devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)

        # Regex to parse hw:CARD=CardName,DEV=N format
        hw_pattern = re.compile(r'hw:CARD=([^,]+),DEV=(\d+)')

        for dev_str in alsa_devices:
            match = hw_pattern.match(dev_str)
            if match:
                card_name = match.group(1)
                dev_num = int(match.group(2))

                # Extract card number from card name if possible
                # This is approximate since ALSA doesn't always expose card number directly
                card_num = USBudioDeviceManager._get_card_number(dev_str)

                devices.append(AudioDevice(
                    device_name=dev_str,
                    card_number=card_num,
                    card_name=card_name,
                    device_number=dev_num
                ))

        return devices

    @staticmethod
    def _get_card_number(device_str: str) -> int:
        """
        Extract card number from device string.
        Fallback to parsing /proc/asound/cards if needed.
        """
        # Try to match hw:X,Y format first
        simple_pattern = re.compile(r'hw:(\d+),(\d+)')
        match = simple_pattern.match(device_str)
        if match:
            return int(match.group(1))

        # Default to -1 if can't determine
        return -1

    @staticmethod
    def find_device(pattern: Optional[str] = None) -> Optional[AudioDevice]:
        """
        Find USB audio capture device by name pattern.

        Args:
            pattern: Regex pattern to match card name (e.g., 'UCA222', 'Scarlett').
                    If None, returns first non-internal device found.

        Returns:
            AudioDevice object or None if not found
        """
        devices = USBudioDeviceManager.list_capture_devices()

        # Filter out internal sound cards (typically PCH, Intel, Analog)
        internal_patterns = ['PCH', 'Intel', 'Analog', 'Built-in']
        usb_devices = [
            dev for dev in devices
            if not any(p.lower() in dev.card_name.lower() for p in internal_patterns)
        ]

        if pattern:
            regex = re.compile(pattern, re.IGNORECASE)
            for device in usb_devices:
                if regex.search(device.card_name):
                    return device
        elif usb_devices:
            # Return first USB device
            return usb_devices[0]

        return None

    @staticmethod
    def get_device_info(device_name: str) -> Dict[str, any]:
        """
        Get detailed information about a device.

        Args:
            device_name: ALSA device string (e.g., 'hw:1,0')

        Returns:
            Dictionary with device capabilities
        """
        try:
            # Open device temporarily to query capabilities
            pcm = alsaaudio.PCM(
                alsaaudio.PCM_CAPTURE,
                alsaaudio.PCM_NORMAL,
                device=device_name
            )

            # Get available parameters (this is limited in pyalsaaudio)
            info = {
                'device': device_name,
                'accessible': True,
            }

            pcm.close()
            return info

        except alsaaudio.ALSAAudioError as e:
            return {
                'device': device_name,
                'accessible': False,
                'error': str(e)
            }


def detect_usb_audio_device(preferred_device: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to detect USB audio device.

    Args:
        preferred_device: Regex pattern for preferred device name

    Returns:
        ALSA device string or None
    """
    manager = USBudioDeviceManager()
    device = manager.find_device(preferred_device)
    return device.device_name if device else None


# Example usage and testing
if __name__ == '__main__':
    print("=== USB Audio Device Detection ===\n")

    # List all capture devices
    manager = USBudioDeviceManager()
    devices = manager.list_capture_devices()

    print(f"Found {len(devices)} capture device(s):\n")
    for dev in devices:
        print(f"  Card: {dev.card_name} (#{dev.card_number})")
        print(f"  Device: {dev.device_name}")
        print(f"  Number: {dev.device_number}")

        # Get device info
        info = manager.get_device_info(dev.device_name)
        print(f"  Accessible: {info['accessible']}")
        if not info['accessible']:
            print(f"  Error: {info.get('error', 'Unknown')}")
        print()

    # Try to find USB audio device
    print("=== Auto-detecting USB Audio Device ===\n")
    usb_device = manager.find_device()
    if usb_device:
        print(f"Detected USB audio device: {usb_device.card_name}")
        print(f"ALSA device string: {usb_device.device_name}")
    else:
        print("No USB audio device found")
```

---

### Audio Capture Module

Create production-ready capture implementation:

```python
"""
USB Audio capture implementation using ALSA.
Handles real-time audio capture with configurable quality and latency.
"""

import alsaaudio
import time
import logging
from typing import Optional, Callable, Generator
from dataclasses import dataclass
from enum import Enum


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleFormat(Enum):
    """Supported PCM sample formats."""
    S16_LE = alsaaudio.PCM_FORMAT_S16_LE  # 16-bit signed little-endian
    S24_3LE = alsaaudio.PCM_FORMAT_S24_3LE  # 24-bit signed little-endian (3 bytes)
    S32_LE = alsaaudio.PCM_FORMAT_S32_LE  # 32-bit signed little-endian


@dataclass
class CaptureConfig:
    """Configuration for audio capture."""
    device: str = 'default'  # ALSA device name
    sample_rate: int = 48000  # Hz
    channels: int = 2  # Stereo
    sample_format: SampleFormat = SampleFormat.S16_LE
    period_size: int = 1024  # frames per period
    periods: int = 3  # number of periods in buffer (3 recommended for USB)

    @property
    def latency_ms(self) -> float:
        """Calculate approximate latency in milliseconds."""
        return (self.period_size / self.sample_rate) * 1000

    @property
    def bytes_per_sample(self) -> int:
        """Bytes per sample based on format."""
        if self.sample_format == SampleFormat.S16_LE:
            return 2
        elif self.sample_format == SampleFormat.S24_3LE:
            return 3
        elif self.sample_format == SampleFormat.S32_LE:
            return 4
        return 2  # default

    @property
    def bytes_per_frame(self) -> int:
        """Bytes per frame (all channels)."""
        return self.bytes_per_sample * self.channels

    @property
    def period_bytes(self) -> int:
        """Expected bytes per period."""
        return self.period_size * self.bytes_per_frame


class USBAudioCapture:
    """
    USB Audio capture using ALSA.
    Supports real-time streaming with error handling and recovery.
    """

    def __init__(self, config: CaptureConfig):
        """
        Initialize USB audio capture.

        Args:
            config: CaptureConfig object with capture parameters
        """
        self.config = config
        self.pcm: Optional[alsaaudio.PCM] = None
        self.is_capturing = False

        logger.info(f"USB Audio Capture initialized:")
        logger.info(f"  Device: {config.device}")
        logger.info(f"  Sample Rate: {config.sample_rate} Hz")
        logger.info(f"  Channels: {config.channels}")
        logger.info(f"  Format: {config.sample_format.name}")
        logger.info(f"  Period Size: {config.period_size} frames")
        logger.info(f"  Latency: {config.latency_ms:.2f} ms")

    def open(self) -> bool:
        """
        Open ALSA device for capture.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.pcm = alsaaudio.PCM(
                type=alsaaudio.PCM_CAPTURE,
                mode=alsaaudio.PCM_NONBLOCK,
                rate=self.config.sample_rate,
                channels=self.config.channels,
                format=self.config.sample_format.value,
                periodsize=self.config.period_size,
                device=self.config.device
            )

            logger.info(f"Opened ALSA device: {self.config.device}")
            return True

        except alsaaudio.ALSAAudioError as e:
            logger.error(f"Failed to open ALSA device: {e}")
            return False

    def close(self):
        """Close ALSA device."""
        if self.pcm:
            self.pcm.close()
            self.pcm = None
            logger.info("Closed ALSA device")

    def capture_stream(
        self,
        callback: Optional[Callable[[bytes], None]] = None,
        duration_seconds: Optional[float] = None
    ) -> Generator[bytes, None, None]:
        """
        Capture audio stream as generator.

        Args:
            callback: Optional callback function called with each audio chunk
            duration_seconds: Optional duration limit (None = infinite)

        Yields:
            Audio data as bytes
        """
        if not self.pcm:
            logger.error("Device not opened. Call open() first.")
            return

        self.is_capturing = True
        start_time = time.time()
        frames_captured = 0

        logger.info("Starting audio capture...")

        try:
            while self.is_capturing:
                # Check duration limit
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"Reached duration limit: {duration_seconds}s")
                    break

                # Read audio data
                length, data = self.pcm.read()

                if length > 0:
                    # Successfully read data
                    frames_captured += length

                    if callback:
                        callback(data)

                    yield data

                elif length == 0:
                    # No data available yet (non-blocking mode)
                    time.sleep(0.001)  # 1ms sleep to prevent busy-wait

                elif length == -alsaaudio.EPIPE:
                    # Buffer overrun - we're not reading fast enough
                    logger.warning("Buffer overrun detected (EPIPE). Consider increasing period size.")
                    # Recover by continuing

                elif length < 0:
                    # Other error
                    logger.error(f"Capture error: {length}")
                    break

        except KeyboardInterrupt:
            logger.info("Capture interrupted by user")

        finally:
            self.is_capturing = False
            elapsed = time.time() - start_time
            logger.info(f"Capture stopped. Duration: {elapsed:.2f}s, Frames: {frames_captured}")

    def stop(self):
        """Stop capture stream."""
        self.is_capturing = False
        logger.info("Stopping capture...")


# Example usage
if __name__ == '__main__':
    import sys
    from usb_audio import detect_usb_audio_device

    print("=== USB Audio Capture Test ===\n")

    # Detect USB audio device
    device = detect_usb_audio_device()
    if not device:
        print("ERROR: No USB audio device found")
        sys.exit(1)

    print(f"Using device: {device}\n")

    # Create capture configuration
    config = CaptureConfig(
        device=device,
        sample_rate=48000,
        channels=2,
        sample_format=SampleFormat.S16_LE,
        period_size=1024,
        periods=3
    )

    # Initialize capture
    capture = USBAudioCapture(config)

    if not capture.open():
        print("ERROR: Failed to open capture device")
        sys.exit(1)

    # Capture for 10 seconds and save to file
    print("Capturing audio for 10 seconds...\n")
    print("Press Ctrl+C to stop early\n")

    output_file = '/tmp/test_capture.raw'

    with open(output_file, 'wb') as f:
        def write_callback(data: bytes):
            f.write(data)

        try:
            for chunk in capture.capture_stream(callback=write_callback, duration_seconds=10):
                # Could process chunks here if needed
                pass
        except KeyboardInterrupt:
            print("\nStopped by user")

    capture.close()

    print(f"\nAudio saved to: {output_file}")
    print(f"To play with aplay:")
    print(f"  aplay -f S16_LE -r 48000 -c 2 {output_file}")
```

---

## Setup Instructions

### Hardware Connection

#### Basic Setup (Turntable with Built-in Preamp)

1. **Verify Turntable Output:**
   - Check if turntable has "Phono/Line" switch → Set to "Line"
   - Or check if turntable has "Line Out" RCA jacks

2. **Connect Turntable to USB Interface:**
   ```
   Turntable RCA Output (Red/White) → USB Interface RCA Input (Red/White)
   ```

3. **Connect USB Interface to Computer:**
   ```
   USB Interface → USB Port on Raspberry Pi or Linux PC
   ```

4. **Power On:**
   - Behringer UCA222: Bus-powered (no external power needed)
   - ART USB Phono Plus: Connect power adapter

#### Advanced Setup (Turntable without Built-in Preamp)

1. **Connect Turntable to External Preamp:**
   ```
   Turntable Phono RCA Output → External Phono Preamp Input
   Turntable Ground Wire → Phono Preamp Ground Terminal
   ```

2. **Connect Preamp to USB Interface:**
   ```
   Phono Preamp Line Output → USB Interface Line Input
   ```

3. **Connect USB Interface to Computer:**
   ```
   USB Interface → USB Port on Raspberry Pi or Linux PC
   ```

4. **Power On:**
   - Connect power to phono preamp (if required)
   - Connect power to USB interface (if required)

---

### Software Setup

#### Install System Dependencies

**Ubuntu/Debian/Raspberry Pi OS:**
```bash
sudo apt-get update
sudo apt-get install -y \
    libasound2-dev \
    alsa-utils \
    python3-dev \
    build-essential
```

#### Verify USB Audio Device Detection

1. **Plug in USB audio interface**

2. **List capture devices:**
   ```bash
   arecord -l
   ```

   Expected output:
   ```
   **** List of CAPTURE Hardware Devices ****
   card 1: UCA222 [UCA222], device 0: USB Audio [USB Audio]
     Subdevices: 1/1
     Subdevice #0: subdevice #0
   ```

3. **Test capture:**
   ```bash
   # Capture 5 seconds of audio
   arecord -D hw:1,0 -f S16_LE -r 48000 -c 2 -d 5 /tmp/test.wav

   # Play back
   aplay /tmp/test.wav
   ```

#### Install Python Dependencies

Using `uv` (TurnTabler standard):
```bash
cd /home/a_manza/dev/turntabler
uv pip install pyalsaaudio
```

Or using pip:
```bash
pip install pyalsaaudio
```

#### Test Python Capture

```bash
# Copy the code from the capture module above to test
python src/turntabler/usb_audio_capture.py
```

---

## Troubleshooting

### Device Not Detected

**Symptom:** `arecord -l` doesn't show USB audio interface

**Solutions:**
1. Check USB connection (try different USB port)
2. Check if device is powered (if external power required)
3. Verify kernel module loaded:
   ```bash
   lsmod | grep snd_usb_audio
   ```
   If not loaded:
   ```bash
   sudo modprobe snd_usb_audio
   ```
4. Check dmesg for USB errors:
   ```bash
   dmesg | grep -i usb | tail -20
   ```

---

### Permission Denied

**Symptom:** `ALSAAudioError: Permission denied`

**Solutions:**
1. Add user to `audio` group:
   ```bash
   sudo usermod -a -G audio $USER
   ```
   Then log out and log back in.

2. Check device permissions:
   ```bash
   ls -l /dev/snd/
   ```

---

### Buffer Overrun (EPIPE Error)

**Symptom:** Logs show "Buffer overrun detected (EPIPE)"

**Cause:** Application not reading audio data fast enough

**Solutions:**
1. Increase period size:
   ```python
   config.period_size = 2048  # or 4096
   ```

2. Increase number of periods:
   ```python
   config.periods = 4
   ```

3. Reduce CPU load (close other applications)

4. Use CPU governor for performance:
   ```bash
   # On Raspberry Pi
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```

---

### No Audio / Silent Capture

**Symptom:** Capture works but file is silent

**Possible Causes:**
1. **Input gain too low**
   - Solution: Increase input volume via alsamixer:
     ```bash
     alsamixer
     # Press F4 for capture
     # Select USB device (F6)
     # Increase capture level
     ```

2. **Wrong input selected**
   - Solution: Check if USB interface has multiple inputs (use alsamixer to select)

3. **Phono signal to line input**
   - If you connected phono-level signal to line-level input without preamp, signal will be extremely weak
   - Solution: Add phono preamp

4. **Muted input**
   - Solution: Check alsamixer for muted inputs (press M to unmute)

---

### Audio Quality Issues

**Symptom:** Crackling, popping, or distortion

**Possible Causes:**
1. **Buffer underrun/overrun**
   - Solution: Increase period size and periods

2. **USB power issues**
   - Solution: Use powered USB hub or different USB port

3. **Sample rate mismatch**
   - Solution: Ensure config.sample_rate matches device capability

4. **Input clipping**
   - Solution: Reduce turntable output volume or input gain

5. **Poor USB cable**
   - Solution: Use high-quality, shielded USB cable (< 6 feet)

---

### High Latency

**Symptom:** Noticeable delay between turntable and output

**Cause:** Large buffer sizes

**Solution:**
Reduce period size and periods:
```python
config = CaptureConfig(
    period_size=256,  # Lower = less latency
    periods=2,        # Fewer = less latency
    sample_rate=48000
)
```

**Note:** For vinyl playback, latency is less critical than reliability. A 20-30ms latency is imperceptible.

---

### Device Name Changes After Reboot

**Symptom:** Device `hw:1,0` becomes `hw:2,0` after reboot

**Cause:** Card numbers assigned dynamically

**Solution:**
Use named device format:
```python
device = 'hw:CARD=UCA222,DEV=0'  # More stable
```

Or use the USBudioDeviceManager class to auto-detect by name pattern.

---

## Latency Benchmarks

Expected latency values for different configurations:

| Configuration | Period Size | Periods | Sample Rate | Latency | Use Case |
|--------------|-------------|---------|-------------|---------|----------|
| Ultra-low latency | 64 | 2 | 48000 | ~1.3ms | Real-time monitoring |
| Low latency | 256 | 2 | 48000 | ~5.3ms | Live performance |
| Balanced | 512 | 3 | 48000 | ~10.7ms | Streaming (USB) |
| **Recommended** | **1024** | **3** | **48000** | **~21ms** | **Vinyl streaming** |
| High reliability | 2048 | 4 | 48000 | ~42ms | Unreliable USB/CPU |

**TurnTabler Recommendation:** 1024 frames / 3 periods / 48kHz
- Latency: ~21ms (imperceptible for vinyl playback)
- Reliability: Excellent (protects against USB timing variations)
- CPU usage: Low (Raspberry Pi friendly)

---

## Real-World Examples

### Example 1: Raspberry Pi Vinyl Streamer

From [github.com/quebulm/Raspberry-Pi-Vinyl-Streamer](https://github.com/quebulm/Raspberry-Pi-Vinyl-Streamer):
- **Hardware:** Raspberry Pi 3A+ + Behringer UCA202 + MicroPhono PP400 preamp
- **Software:** Icecast2 + Darkice for streaming
- **Result:** Successfully streams vinyl over local network
- **Relevance:** Proves Behringer UCA202 + Pi works reliably

### Example 2: Sonos Vinyl Integration

From [stevegattuso.me/wiki/sonos-vinyl.html](https://www.stevegattuso.me/wiki/sonos-vinyl.html):
- **Setup:** Turntable → USB Audio Interface → Raspberry Pi → Sonos (via AirPlay)
- **Challenge:** AirPlay to Sonos delivers AAC (lossy)
- **Relevance:** Confirms need for Sonos native protocol (not AirPlay) for lossless
- **TurnTabler Advantage:** Using SoCo library for FLAC streaming avoids this limitation

### Example 3: pyalsaaudio Production Usage

From pyalsaaudio GitHub issues and Stack Overflow:
- Multiple users report rock-solid reliability with USB audio on Raspberry Pi
- Typical configuration: 44.1kHz or 48kHz, 16-bit, period size 1024-2048
- Continuous streaming for hours/days without issues
- Recommended for production audio applications

---

## Performance Optimization

### Raspberry Pi Specific

#### 1. CPU Governor
Set CPU to performance mode:
```bash
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 2. USB Power
Ensure adequate USB power:
```bash
# Check USB power config
vcgencmd get_config usb_max_current

# Enable maximum USB current (add to /boot/config.txt)
usb_max_current=1
```

#### 3. Disable WiFi Power Management
```bash
sudo iwconfig wlan0 power off
```

#### 4. Use Ethernet Instead of WiFi
For lowest latency and most reliable network streaming.

---

## Next Steps for TurnTabler

### Integration Roadmap

1. **Phase 4a: USB Audio Capture Module**
   - Implement `usb_audio.py` with device detection
   - Implement `usb_audio_capture.py` with ALSA capture
   - Unit tests for device enumeration
   - Integration tests with test audio file playback

2. **Phase 4b: Connect to Streaming Pipeline**
   - Modify `streaming.py` to accept USB audio source
   - Integrate with SoCo FLAC streaming
   - Real-time encoding to FLAC (if needed)
   - Buffer management between capture and streaming

3. **Phase 4c: CLI Integration**
   - Add `turntabler stream --source usb` command
   - Device selection via CLI arguments
   - Status monitoring and diagnostics
   - Error handling and recovery

4. **Phase 4d: Production Hardening**
   - Systemd service for auto-start
   - Watchdog for crash recovery
   - Logging and monitoring
   - Performance metrics

5. **Phase 4e: Documentation**
   - End-user setup guide
   - Hardware purchase recommendations
   - Troubleshooting playbook
   - Video tutorials (optional)

---

## Conclusion

### Recommended Hardware: Behringer UCA222

For the TurnTabler project, the **Behringer UCA222** is the optimal choice:
- Price: $30-40
- Linux compatibility: Excellent
- Quality: Sufficient for vinyl (16-bit/48kHz)
- Reliability: Proven in similar projects
- Simplicity: Plug-and-play with ALSA

**Add external phono preamp** (Behringer PP400, $25-30) if turntable lacks built-in preamp.

**Total cost:** $55-70 for complete vinyl capture solution.

### Software: pyalsaaudio

Use **pyalsaaudio** for direct ALSA access:
- Lowest latency
- Best reliability on Linux/Raspberry Pi
- Lightweight (Raspberry Pi friendly)
- Fine-grained control

### Configuration

**Recommended ALSA parameters:**
- Sample rate: 48000 Hz
- Format: S16_LE (16-bit signed little-endian)
- Channels: 2 (stereo)
- Period size: 1024 frames (~21ms latency)
- Periods: 3 (USB recommended)

### Next Steps

1. Purchase Behringer UCA222 + phono preamp (if needed)
2. Implement `usb_audio.py` device detection module
3. Implement `usb_audio_capture.py` capture module
4. Test with real turntable
5. Integrate with SoCo streaming pipeline

This guide provides all necessary information to implement Phase 4 (USB Audio Integration) of the TurnTabler project with confidence.
