"""
FastAPI server that streams looping FLAC audio to Sonos devices.
Simulates continuous turntable audio output.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
from pathlib import Path

app = FastAPI()

# Path to test audio file in project root
AUDIO_FILE = Path(__file__).parent.parent.parent / "test-loop.flac"


@app.get("/turntable.flac")
async def stream_turntable():
    """Stream looping FLAC file - simulates endless turntable audio"""

    async def generate():
        """Generator that loops audio file indefinitely"""
        chunk_size = 4096

        while True:
            try:
                with open(AUDIO_FILE, "rb") as f:
                    # Read FLAC header once
                    header = f.read(chunk_size)
                    yield header

                    # Stream rest of file
                    while chunk := f.read(chunk_size):
                        yield chunk
                        await asyncio.sleep(0.001)  # Prevent blocking

                # File finished, loop back (no gap in audio)
                print("♻️  Looping audio file...")

            except Exception as e:
                print(f"❌ Error streaming: {e}")
                break

    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "none",
            # Fake huge content length for continuous stream
            "Content-Length": "999999999999",
        },
    )


@app.get("/")
async def root():
    return {
        "status": "TurnTabler POC Streaming Server",
        "stream_url": "/turntable.flac",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎵 Starting streaming server on http://0.0.0.0:8000")
    print("📻 Stream URL: http://0.0.0.0:8000/turntable.flac")
    uvicorn.run(app, host="0.0.0.0", port=8000)
