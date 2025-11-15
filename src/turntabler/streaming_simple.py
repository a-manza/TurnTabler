"""
Simple FLAC file server - serves the file once with proper headers.
Use this to test if Sonos can play FLAC files at all.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

AUDIO_FILE = Path(__file__).parent.parent.parent / "test-loop.flac"


@app.get("/turntable.flac")
async def stream_turntable():
    """Serve FLAC file with proper headers"""
    if not AUDIO_FILE.exists():
        return {"error": f"Audio file not found: {AUDIO_FILE}"}

    file_size = AUDIO_FILE.stat().st_size
    print(f"📁 Serving {AUDIO_FILE.name} ({file_size} bytes)")

    return FileResponse(
        AUDIO_FILE,
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
        },
    )


@app.get("/")
async def root():
    return {
        "status": "TurnTabler Simple Streaming Server",
        "stream_url": "/turntable.flac",
        "note": "Serves FLAC file once (no looping) to test basic compatibility",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎵 Starting simple streaming server on http://0.0.0.0:8000")
    print("📻 Stream URL: http://0.0.0.0:8000/turntable.flac")
    print("📝 Note: Serves file once (no looping)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
