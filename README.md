# turntabler

Stream vinyl records to Sonos speakers with lossless audio quality.

## SoCo POC - Continuous FLAC Streaming

This POC validates that we can stream continuous, indefinite-length FLAC audio to Sonos devices using the SoCo library (Sonos native protocol).

### Prerequisites

- Linux (Ubuntu 22.04 or similar)
- ffmpeg and sox: `sudo apt install ffmpeg sox`
- Sonos device on the same network
- Python 3.13+ (uv will handle this)

### CRITICAL FIX 1: Sonos Grouping Handling

**If your Sonos device is grouped with other speakers** (e.g., Beam + Sub):
- ✅ **FIXED** - All control scripts now properly detect groups and use the coordinator
- Grouped devices require sending commands to the **group coordinator**, not individual speakers
- All scripts automatically identify the coordinator and send commands there

**Before fix:** Commands to grouped members were ignored → "PLAYING but no audio"
**After fix:** Commands go to coordinator → Proper playback

---

### CRITICAL FIX 2: force_radio Parameter & Continuous Streaming

**Discovery:** `force_radio=True` tells Sonos "this is a radio stream" expecting ICY metadata (SHOUTcast protocol)

**Single File Playback:**
- Without `force_radio=True`: Plays finite file, stops after it ends ✓
- Works perfectly for single files

**Continuous Streaming (Turntable):**
- Requires `force_radio=True` for radio-mode infinite streaming
- Requires ICY metadata headers (SHOUTcast protocol)
- ✅ Implemented in `streaming_icy.py`

**How it works:**
- `streaming_icy.py` detects `icy-metadata: 1` request header
- Sends ICY response headers and metadata blocks
- Enables Sonos to treat stream as radio (continuous, indefinite)
- Loops FLAC file infinitely with proper protocol support

---

### Testing Continuous Streaming (Phase 2 - Turntable Ready)

**For infinite/continuous streaming (like turntable):**

**Terminal 1 - Start ICY streaming server:**
```bash
source .venv/bin/activate
python -m turntabler.streaming_icy
```

**Terminal 2 - Test continuous playback:**
```bash
source .venv/bin/activate
python -m turntabler.control
```

**Expected behavior:**
- Starts playing immediately
- Loops continuously (after 30 seconds, repeats)
- Can pause/play/stop via Sonos app
- No gaps or dropouts
- Run for 10+ minutes to validate stability

**Success criteria:**
- ✅ Stream plays indefinitely
- ✅ No audio dropouts
- ✅ Clean pause/play/stop controls
- ✅ Looping is seamless

---

### Systematic Debugging Guide (Phase 1 - Reference)

**IMPORTANT:** "PLAYING" status ≠ actual audio. We're debugging why Sonos reports PLAYING but no sound.

**1. Setup environment (one time):**

```bash
cd /home/a_manza/dev/turntabler
uv venv
source .venv/bin/activate
uv pip install -e .
```

**2. Regenerate test audio files with proper specifications:**

```bash
chmod +x regenerate_test_audio.sh
./regenerate_test_audio.sh
```

This creates:
- `test-loop.flac` - 48kHz, 16-bit, stereo (Sonos spec)
- `test-loop.wav` - Same but uncompressed (control test)

**3. TEST 1: Verify Sonos works with any audio at all**

```bash
# Terminal 2 (in new shell)
source .venv/bin/activate
python -m turntabler.test_known_uri
```

This tests BBC Radio 4 (public stream). If this works:
- ✅ SoCo + Sonos infrastructure is fine
- ❌ Problem is specific to our file/server

If this fails:
- ❌ Sonos configuration issue (device muted, wrong network, etc.)

**4. TEST 2: Start debug streaming server (Terminal 1)**

```bash
source .venv/bin/activate
python -m turntabler.streaming_debug
```

Watch the logs for detailed request information.

**5. TEST 3: Test simple FLAC file once**

```bash
# Terminal 2
source .venv/bin/activate
python -m turntabler.streaming_simple
```

Then in Terminal 3:
```bash
source .venv/bin/activate
python -m turntabler.control
```

**6. TEST 4: Test WAV format (if FLAC fails)**

```bash
# Terminal 2 (if not already running)
source .venv/bin/activate
python -m turntabler.streaming_debug
```

Then Terminal 3:
```bash
source .venv/bin/activate
python -m turntabler.test_wav
```

If WAV works but FLAC doesn't → FLAC encoding issue
If WAV doesn't work either → broader issue

### Testing Order (Follow This)

1. **TEST 1 first** - Public radio (2 min) - Validates infrastructure
2. **TEST 2 setup** - Debug server (stay running) - Reveals request patterns
3. **TEST 3 next** - FLAC simple (2 min) - Does our FLAC work?
4. **TEST 4 if needed** - WAV format (2 min) - Isolate codec issue

Each test should take 1-2 minutes. Combined diagnosis time: ~10 minutes.

### Success Criteria

**Phase 1 (Simple Test - CURRENT):**
- ✅ Audio plays on Sonos (even once)
- ✅ State transitions to PLAYING
- ✅ Can hear the 440Hz tone

**Phase 2 (Continuous Streaming - LATER):**
- ✅ Stream runs for 10+ minutes without dropouts
- ✅ Latency acceptable (< 2 seconds)
- ✅ Audio quality is good (lossless FLAC)
- ✅ Can stop and restart stream

### Project Structure

```
src/turntabler/
  streaming.py        # FastAPI server - simple looping (not ICY)
  streaming_simple.py # FastAPI server - single file serve (no looping)
  streaming_debug.py  # FastAPI server - with detailed logging
  streaming_icy.py    # FastAPI server - ICY metadata for continuous streaming ⭐
  control.py          # SoCo control script for Sonos (with group handling)
  test_known_uri.py   # Test script - public radio stream
  test_wav.py         # Test script - WAV format
test-loop.flac        # Test audio file (30s, 440Hz tone, Sonos-optimized)
test-loop.wav         # Test audio file (30s, 440Hz tone, uncompressed)
```

**For turntable use:** Use `streaming_icy.py` with `control.py`

### Technical Details

- **Protocol:** Sonos native (UPnP/HTTP)
- **Codec:** FLAC (lossless)
- **Sample Rate:** 48kHz, stereo
- **Streaming:** Chunked transfer encoding, infinite loop
- **Device Control:** SoCo library with `force_radio=True`

### Troubleshooting

**Stuck in TRANSITIONING/BUFFERING state (no audio):**
1. Start with `streaming_simple.py` instead of looping server
2. Check Content-Length header is correct (should be file size, not fake)
3. Verify FLAC file is valid: `ffprobe test-loop.flac`
4. Try removing `force_radio=True` in control.py for simple test
5. Check server logs for "Error streaming" messages

**No Sonos devices found:**
```bash
# Check device is on network
ping 192.168.86.63

# Try specifying IP directly
python -c "from soco import SoCo; s = SoCo('192.168.86.63'); print(s.player_name)"
```

**Stream won't start:**
```bash
# Verify server is running
curl http://localhost:8000/

# Check server logs
# Monitor for API calls in server terminal

# Check firewall allows port 8000
sudo ufw allow 8000/tcp
```

**Can't hear audio (but status says PLAYING):**
- Check volume on Sonos device
- Try a different audio file to verify speakers work
- Check system audio isn't muted

**Audio quality issues (after continuous streaming works):**
Check FLAC encoding is valid:
```bash
ffprobe test-loop.flac
```

### Next Steps

After successful POC validation:
1. Implement full SoCo backend in `src/turntabler/backends/`
2. Add USB audio capture for turntable input
3. Create CLI interface
4. Test on Raspberry Pi 5