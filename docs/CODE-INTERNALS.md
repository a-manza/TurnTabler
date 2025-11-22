# TurnTabler: Code Internals

How the TurnTabler Python implementation processes audio from USB capture to Sonos streaming.

---

## Module Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        cli.py                                │
│                    (Entry Point)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    streaming.py                              │
│              (TurnTablerStreamer Orchestrator)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Audio Setup │  │ Server Mgmt │  │ Sonos Ctrl  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                │
┌─────────────────┐ ┌─────────────────┐     │
│ audio_source.py │ │streaming_wav.py │     │
│                 │ │                 │     │
│ USBAudioSource  │ │WAVStreamingServer     │
│ SyntheticSource │ │ FastAPI app     │     │
│ FileSource      │ │                 │     │
└────────┬────────┘ └─────────────────┘     │
         │                                  │
         ▼                                  │
┌─────────────────┐                         │
│usb_audio_capture│                         │
│                 │                         │
│ USBAudioCapture │                         │
│ (pyalsaaudio)   │                         │
└─────────────────┘                         │
                                            │
┌─────────────────┐                         │
│  usb_audio.py   │◀────────────────────────┘
│                 │    (device detection)
│USBAudioDevice   │
│Manager          │
└─────────────────┘
```

---

## Execution Flow

### Phase 1: CLI Entry

```python
# cli.py: stream()

@app.command()
def stream(synthetic, file, device, sonos_ip, ...):
    # 1. Determine source type
    if synthetic:
        source_type = "synthetic"
    elif file:
        source_type = f"file:{file}"
    else:
        source_type = "usb"  # Default

    # 2. Create orchestrator
    streamer = TurnTablerStreamer(
        sonos_ip=sonos_ip,
        port=port,
        stream_name=stream_name,
    )

    # 3. Run complete pipeline
    stats = streamer.run(audio_source=source_type, device=device)
```

---

### Phase 2: Orchestrator Pipeline

```python
# streaming.py: TurnTablerStreamer.run()

def run(self, audio_source, device):
    # Step 1: Initialize audio capture
    self.setup_audio_source(audio_source, device)

    # Step 2: Create HTTP server
    self.setup_streaming_server()

    # Step 3: Start server in background thread
    self.start_http_server_background()

    # Step 4: Connect to Sonos
    self.setup_sonos()

    # Step 5: Tell Sonos to play our stream
    self.start_streaming()

    # Step 6: Monitor until stopped
    self.monitor_streaming()

    # Step 7: Cleanup
    self.audio_source.close()
    self.sonos.stop()
```

**Sequence Diagram:**

```
    cli.py          streaming.py        audio_source.py      streaming_wav.py       Sonos
       │                  │                    │                    │                 │
       │   run()          │                    │                    │                 │
       │─────────────────▶│                    │                    │                 │
       │                  │                    │                    │                 │
       │                  │ USBAudioSource()   │                    │                 │
       │                  │───────────────────▶│                    │                 │
       │                  │                    │                    │                 │
       │                  │ WAVStreamingServer()                    │                 │
       │                  │───────────────────────────────────────▶│                 │
       │                  │                    │                    │                 │
       │                  │ uvicorn.run() [thread]                  │                 │
       │                  │───────────────────────────────────────▶│                 │
       │                  │                    │                    │                 │
       │                  │ play_uri()         │                    │                 │
       │                  │────────────────────────────────────────────────────────▶│
       │                  │                    │                    │                 │
       │                  │                    │   GET /stream.wav  │                 │
       │                  │                    │◀───────────────────────────────────│
       │                  │                    │                    │                 │
       │                  │                    │   read_chunk()     │                 │
       │                  │                    │◀───────────────────│                 │
       │                  │                    │                    │                 │
       │                  │ monitor loop       │                    │                 │
       │                  │◀ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │                 │
       │                  │                    │                    │                 │
```

---

### Phase 3: Audio Source Initialization

```python
# audio_source.py: USBAudioSource.__init__()

def __init__(self, format, device=None):
    # 1. Auto-detect USB device if not specified
    if device is None:
        device = detect_usb_audio_device()
        # Returns: "hw:CARD=UCA222,DEV=0"

    # 2. Configure ALSA capture
    config = CaptureConfig(
        device=device,
        sample_rate=48000,
        channels=2,
        sample_format=SampleFormat.S16_LE,
        period_size=1024,
        periods=3,
    )

    # 3. Create capture object
    self.capture = USBAudioCapture(config)
    self.capture.open()

    # 4. Start generator for streaming reads
    self._stream = self.capture.capture_stream()
```

```python
# usb_audio_capture.py: USBAudioCapture

def open(self):
    # Create ALSA PCM device
    self.pcm = alsaaudio.PCM(
        type=alsaaudio.PCM_CAPTURE,
        mode=alsaaudio.PCM_NONBLOCK,
        device=self.config.device,
    )
    # Configure format, rate, channels, periods...

def capture_stream(self):
    # Generator that yields audio chunks
    while self.is_capturing:
        length, data = self.pcm.read()
        if length > 0:
            yield data
        else:
            time.sleep(0.001)  # Prevent busy-wait
```

---

### Phase 4: HTTP Server Setup

```python
# streaming_wav.py: WAVStreamingServer

def __init__(self, audio_source, wav_format, stream_name):
    self.audio_source = audio_source
    self.wav_format = wav_format

    # Create FastAPI app with routes
    self.app = FastAPI()
    self._setup_routes()

def _setup_routes(self):
    @self.app.get("/stream.wav")
    async def stream_wav(request):
        return StreamingResponse(
            self._generate_stream(),
            media_type="audio/wav",
        )

async def _generate_stream(self):
    # 1. Send WAV header first
    header = generate_wav_header(self.wav_format, infinite=True)
    yield header

    # 2. Continuously stream PCM data
    while True:
        # Non-blocking read from audio source
        chunk = await asyncio.to_thread(
            self.audio_source.read_chunk, 4096
        )

        if chunk is None:
            break

        yield chunk
```

**Server Startup:**

```python
# streaming.py: start_http_server_background()

def start_http_server_background(self):
    app = self.server.app

    config = uvicorn.Config(app, host="0.0.0.0", port=5901)
    server = uvicorn.Server(config)

    # Run in daemon thread
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until server accepts connections
    self._wait_for_server_ready(timeout=5)
```

---

### Phase 5: Sonos Connection

```python
# streaming.py: setup_sonos()

def setup_sonos(self):
    # 1. Connect to device
    if self.sonos_ip:
        device = SoCo(self.sonos_ip)
    else:
        device = self.discover_sonos()

    # 2. CRITICAL: Get group coordinator
    if device.group:
        self.sonos = device.group.coordinator
    else:
        self.sonos = device
```

```python
# streaming.py: start_streaming()

def start_streaming(self):
    local_ip = self.get_local_ip()
    stream_url = f"http://{local_ip}:{self.port}/stream.wav"

    # Tell Sonos to fetch our stream
    self.sonos.play_uri(
        uri=stream_url,
        title=self.stream_name,
        start=True,
        force_radio=False,
    )

    # Monitor until PLAYING state
    for i in range(10):
        time.sleep(1)
        state = self.sonos.get_current_transport_info()
        if state["current_transport_state"] == "PLAYING":
            return True
```

---

## Data Flow Through Objects

```
┌─────────────────┐
│ alsaaudio.PCM   │  pcm.read() → (length, bytes)
└────────┬────────┘
         │ raw PCM bytes
         ▼
┌─────────────────┐
│ USBAudioCapture │  capture_stream() → yields bytes
└────────┬────────┘
         │ generator
         ▼
┌─────────────────┐
│ USBAudioSource  │  read_chunk() → next(generator)
└────────┬────────┘
         │ bytes
         ▼
┌─────────────────┐
│WAVStreamingServer│  _generate_stream() → yields chunks
└────────┬────────┘
         │ async generator
         ▼
┌─────────────────┐
│ StreamingResponse│  FastAPI sends via HTTP
└────────┬────────┘
         │ chunked HTTP
         ▼
      [Network]
```

**Chunk Sizes:**

| Component | Size | Notes |
|-----------|------|-------|
| ALSA period | 1024 frames | 4096 bytes (2ch × 2bytes × 1024) |
| read_chunk() | 4096 bytes | Passed to generator |
| HTTP chunk | 4096 bytes | Same as read |
| WAV header | 44 bytes | Sent once at start |

---

## Key Functions Reference

### cli.py
| Function | Purpose |
|----------|---------|
| `stream()` | Main command - parse args, create streamer, run |
| `test_quick()` | 30-second validation test |
| `list_devices()` | Show available USB audio devices |

### streaming.py
| Function | Purpose |
|----------|---------|
| `run()` | Complete orchestration pipeline |
| `setup_audio_source()` | Create USB/Synthetic/File source |
| `setup_streaming_server()` | Create WAVStreamingServer |
| `start_http_server_background()` | Launch uvicorn in thread |
| `setup_sonos()` | Connect + get group coordinator |
| `start_streaming()` | Call play_uri() on Sonos |
| `monitor_streaming()` | Wait loop until Ctrl+C |

### audio_source.py
| Class | Purpose |
|-------|---------|
| `AudioFormat` | Dataclass: sample_rate, channels, bits |
| `USBAudioSource` | Wraps USBAudioCapture with read_chunk() |
| `SyntheticAudioSource` | Generates sine wave for testing |
| `FileAudioSource` | Reads from WAV file (loops) |

### streaming_wav.py
| Function | Purpose |
|----------|---------|
| `generate_wav_header()` | Create 44-byte header with infinite size |
| `WAVStreamingServer` | FastAPI app with /stream.wav endpoint |
| `_generate_stream()` | Async generator yielding audio chunks |

### usb_audio_capture.py
| Function | Purpose |
|----------|---------|
| `USBAudioCapture.open()` | Initialize ALSA PCM device |
| `capture_stream()` | Generator yielding raw PCM from ALSA |
| `stop()` | Signal generator to exit |

---

## Thread Model

```
┌─────────────────────────────────────────┐
│            Main Thread                   │
│                                          │
│  cli.py → streaming.py                   │
│    │                                     │
│    ├── setup_audio_source()              │
│    ├── setup_streaming_server()          │
│    ├── start_http_server_background() ───┼──┐
│    ├── setup_sonos()                     │  │
│    ├── start_streaming()                 │  │
│    └── monitor_streaming() [blocks]      │  │
│                                          │  │
└──────────────────────────────────────────┘  │
                                              │
┌──────────────────────────────────────────┐  │
│         Uvicorn Thread (daemon)          │◀─┘
│                                          │
│  FastAPI app serves /stream.wav          │
│    │                                     │
│    └── _generate_stream()                │
│          └── audio_source.read_chunk()   │
│                (via asyncio.to_thread)   │
│                                          │
└──────────────────────────────────────────┘
```

**Notes:**
- Main thread handles orchestration and waits for Ctrl+C
- Uvicorn thread handles HTTP requests
- `asyncio.to_thread()` prevents blocking the event loop during audio reads
- Daemon thread dies automatically when main exits
