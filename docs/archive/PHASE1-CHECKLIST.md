# Phase 1: Proof of Concept - Implementation Checklist

## Goal
Prove we can stream lossless audio from this Linux machine to Sonos Beam via AirPlay 2, with Python-driven control and modular architecture ready for Raspberry Pi deployment.

## Success Criteria
- [x] Documentation foundation established
- [ ] Tech stack chosen with documented rationale
- [ ] Device discovery working (find Sonos Beam on network)
- [ ] Can stream lossless audio file to Sonos programmatically
- [ ] Audio quality verified as lossless (ALAC codec)
- [ ] Code is modular and well-documented
- [ ] Same code structure will work on Raspberry Pi

---

## Task 1: Tech Stack Evaluation & Decision ⭐

**Status:** In Progress

### Objective
Choose the best Python-controllable approach for lossless AirPlay 2 streaming.

### Evaluation Checklist

#### Option A: VLC
- [ ] Install VLC and RAOP plugin
- [ ] Test basic command-line streaming to Sonos
  ```bash
  cvlc test-audio.flac --sout '#raop{host=SONOS_IP}' --no-sout-video
  ```
- [ ] Verify ALAC codec in use (check logs/Wireshark)
- [ ] Measure latency (time from start to audio output)
- [ ] Test with multiple formats (WAV, FLAC, different bit depths)
- [ ] Test Python subprocess control
- [ ] Test python-vlc bindings (optional)
- [ ] Document results

#### Option B: GStreamer
- [ ] Install GStreamer + plugins
- [ ] Check for raopsink availability
  ```bash
  gst-inspect-1.0 raopsink
  ```
- [ ] Test basic pipeline to Sonos
  ```bash
  gst-launch-1.0 filesrc location=test.flac ! decodebin ! raopsink host=SONOS_IP
  ```
- [ ] Test Python bindings (PyGObject)
- [ ] Compare quality/latency to VLC
- [ ] Document results

#### Option C: PipeWire/PulseAudio (Optional)
- [ ] Check if RAOP module available
- [ ] Test system audio routing to Sonos
- [ ] Document findings (likely defer to Phase 2)

#### Option D: FFmpeg (Optional)
- [ ] Test RAOP output capability
- [ ] Document if viable

### Decision Documentation
- [ ] Create `/docs/implementation/tech-stack-decision.md`
- [ ] Include test results, quality measurements, pros/cons
- [ ] Make recommendation with clear rationale
- [ ] Document why chosen stack is best for our use case

**Decision:** [To be filled after testing]

---

## Task 2: Environment Setup

**Status:** Pending

### Checklist
- [ ] Verify Python 3.13 is available
  ```bash
  python3.13 --version
  ```
- [ ] Install uv package manager
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [ ] Initialize project with uv
  ```bash
  cd /home/a_manza/dev/turntabler
  uv venv --python 3.13
  source .venv/bin/activate
  ```
- [ ] Update pyproject.toml with initial dependencies
  - zeroconf (device discovery)
  - click (CLI framework)
  - Backend-specific libs (based on Task 1 decision)
- [ ] Install dependencies
  ```bash
  uv pip install -e .
  ```
- [ ] Install system packages (VLC/GStreamer based on choice)
- [ ] Test basic imports in Python
- [ ] Create .gitignore for venv, __pycache__, etc.

---

## Task 3: Device Discovery Module

**Status:** Pending
**File:** `src/turntabler/discovery.py`

### Checklist
- [ ] Create module file
- [ ] Implement mDNS scanner using zeroconf
  ```python
  from zeroconf import ServiceBrowser, Zeroconf

  # Search for _raop._tcp.local. services
  ```
- [ ] Parse device information (name, IP, port, capabilities)
- [ ] Filter for AirPlay devices (look for RAOP services)
- [ ] Create AirPlayDevice dataclass/model
- [ ] Implement `discover_devices()` function
- [ ] Implement `find_device_by_name(name)` function
- [ ] Add timeout handling
- [ ] Add error handling (no devices found, network issues)
- [ ] Write unit tests (if time permits)
- [ ] Test manually: Find Sonos Beam on network

### Expected Output
```python
from turntabler.discovery import discover_devices

devices = discover_devices(timeout=5)
for device in devices:
    print(f"{device.name} at {device.ip}:{device.port}")
# Output: Sonos Beam at 192.168.1.100:7000
```

---

## Task 4: Audio Streaming Core

**Status:** Pending
**File:** `src/turntabler/streaming.py` + `src/turntabler/backends/`

### Checklist

#### Streaming Abstraction
- [ ] Create abstract base class for backends
  ```python
  class AudioStreamer(ABC):
      @abstractmethod
      def stream_file(self, file_path: str, device: AirPlayDevice) -> None:
          pass
  ```
- [ ] Define common interface for all backends

#### Backend Implementation (Based on Task 1 Choice)
- [ ] Create `src/turntabler/backends/` directory
- [ ] Implement chosen backend (e.g., `vlc.py`)
- [ ] Handle file path validation
- [ ] Handle device connection
- [ ] Implement start streaming
- [ ] Implement stop streaming
- [ ] Implement status checking (is streaming?)
- [ ] Add error handling (file not found, device unreachable, etc.)
- [ ] Add logging for debugging

#### Audio File Handling
- [ ] Create `src/turntabler/audio.py`
- [ ] Validate audio file formats (WAV, FLAC, ALAC supported)
- [ ] Extract audio metadata (sample rate, bit depth, channels)
- [ ] Helper functions for format conversion if needed

### Testing
- [ ] Test with 16-bit/44.1kHz WAV file
- [ ] Test with 24-bit/48kHz FLAC file
- [ ] Test with different file formats
- [ ] Test error cases (bad file, wrong device IP)
- [ ] Verify audio plays on Sonos Beam
- [ ] No audible artifacts or distortion

---

## Task 5: CLI Interface

**Status:** Pending
**File:** `src/turntabler/cli.py`

### Checklist

#### Commands to Implement
- [ ] `turntabler discover`
  - List all AirPlay devices on network
  - Display name, IP, status

- [ ] `turntabler devices`
  - Show saved/known devices (future: config file)

- [ ] `turntabler stream FILE --device DEVICE_NAME`
  - Stream audio file to specified device
  - Default to "Sonos Beam" if only one device
  - Show progress/status

- [ ] `turntabler stop`
  - Halt active streaming

- [ ] `turntabler status`
  - Show current streaming status
  - Which file, which device, duration

#### CLI Features
- [ ] Use Click framework
- [ ] Colorful output (rich or click.style)
- [ ] Progress indicators during streaming
- [ ] Clear error messages
- [ ] Help text for all commands
- [ ] Version command

#### Configuration
- [ ] Create `src/turntabler/config.py`
- [ ] Support config file (e.g., `~/.turntabler/config.yaml`)
- [ ] Remember last used device
- [ ] Allow setting default device

### Testing
- [ ] Test each command manually
- [ ] Test error cases (no devices, file not found, etc.)
- [ ] Verify help text is clear
- [ ] Test on both Ubuntu (dev) and Pi (future)

---

## Task 6: Quality Validation & Testing

**Status:** Pending
**Deliverable:** `/docs/implementation/quality-report.md`

### Audio Quality Tests
- [ ] Create test audio files
  - 16-bit/44.1kHz WAV (CD quality baseline)
  - 24-bit/48kHz FLAC (target quality)
  - 24-bit/96kHz FLAC (higher than AirPlay max)
  - Audiophile reference tracks

- [ ] Stream each file through TurnTabler to Sonos
- [ ] Subjective listening test
  - Compare to direct Sonos app playback
  - Listen for artifacts, distortion, quality loss
  - Note any audible differences

- [ ] Objective measurements
  - [ ] Verify ALAC codec in use (Wireshark or logs)
  - [ ] Measure latency (< 500ms acceptable)
  - [ ] Check network bandwidth usage
  - [ ] Monitor CPU usage during streaming

- [ ] Long-duration test
  - [ ] Stream entire album (45+ minutes)
  - [ ] Monitor for dropouts, stability issues
  - [ ] Verify consistent quality throughout

### Quality Checklist
- [ ] Lossless codec confirmed (ALAC)
- [ ] 24-bit depth maintained (if source is 24-bit)
- [ ] 48kHz sample rate achieved
- [ ] No audible artifacts
- [ ] Stereo imaging preserved
- [ ] Dynamic range intact
- [ ] Latency acceptable (<500ms)
- [ ] Stable over long durations

### Network Tests
- [ ] Test over WiFi
- [ ] Test over Ethernet (if available)
- [ ] Test with network congestion (download while streaming)
- [ ] Test connection loss recovery

### Documentation
- [ ] Document test methodology
- [ ] Record all measurements
- [ ] Include audio samples if helpful
- [ ] Note any issues discovered
- [ ] Recommendations for production deployment

---

## Task 7: Documentation & Knowledge Capture

**Status:** In Progress
**Deliverables:** Multiple docs

### Documentation Checklist
- [x] `claude.md` - Project knowledge base
- [x] `/docs/research/` - Technical research
  - [x] airplay-protocol.md
  - [x] sender-vs-receiver.md
  - [x] audio-quality.md
- [x] `/docs/linux-setup/` - System setup guides
  - [x] audio-stack-options.md
- [x] `/docs/hardware/` - Hardware documentation
  - [x] raspberry-pi-5-guide.md
- [ ] `/docs/implementation/` - Implementation docs
  - [ ] tech-stack-decision.md
  - [ ] quality-report.md
  - [x] PHASE1-CHECKLIST.md (this file)
  - [ ] phase1-results.md

- [ ] `README.md` - User-facing documentation
  - [ ] Project overview
  - [ ] Installation instructions
  - [ ] Usage guide
  - [ ] Troubleshooting
  - [ ] Future roadmap

- [ ] Code documentation
  - [ ] Docstrings for all modules
  - [ ] Inline comments for complex logic
  - [ ] Type hints throughout

- [ ] Final review
  - [ ] Update claude.md with final decisions
  - [ ] Ensure all findings documented
  - [ ] Clean up any TODOs in code
  - [ ] Prepare for Phase 2 planning

---

## Timeline Estimate

| Task | Estimated Time | Priority |
|------|----------------|----------|
| Task 1: Tech Stack Evaluation | 2-3 hours | CRITICAL |
| Task 2: Environment Setup | 30 min | HIGH |
| Task 3: Device Discovery | 1-2 hours | HIGH |
| Task 4: Streaming Core | 2-3 hours | CRITICAL |
| Task 5: CLI Interface | 1-2 hours | MEDIUM |
| Task 6: Quality Testing | 2-3 hours | HIGH |
| Task 7: Documentation | 1-2 hours | MEDIUM |
| **Total** | **10-16 hours** | |

---

## Dependencies

### System Packages (TBD based on Task 1)
- avahi-daemon (mDNS/service discovery)
- VLC OR GStreamer (based on choice)
- ALSA utils (audio debugging)

### Python Packages
- zeroconf (device discovery)
- click (CLI framework)
- Backend-specific (vlc bindings, PyGObject, or pulsectl)

---

## Blockers & Risks

### Potential Blockers
- [ ] Sonos Beam not discoverable on network
- [ ] RAOP streaming not working (firewall, network issues)
- [ ] Audio quality issues (codec problems)
- [ ] Python 3.13 compatibility issues

### Mitigation
- Network troubleshooting docs in place
- Multiple backend options evaluated
- Can test on Python 3.11 if needed

---

## Next Steps After Phase 1

Once POC is complete and validated:
1. **Phase 2:** System audio routing (any Linux audio → Sonos)
2. **Phase 3:** Deploy to Raspberry Pi (same codebase)
3. **Phase 4:** USB audio interface integration (turntable input)
4. **Phase 5:** Production features (web UI, multi-room, monitoring)

---

## Notes

- Keep scope focused on POC - don't add features prematurely
- Prioritize quality and documentation over speed
- Design for modularity - easy to swap backends later
- Test frequently - don't wait until the end
- Ask questions if blocked - don't spin wheels
