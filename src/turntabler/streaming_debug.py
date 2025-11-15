"""
FastAPI streaming server with detailed debug logging.
Helps understand how Sonos fetches and buffers the file.
"""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pathlib import Path
import logging

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

AUDIO_FILE = Path(__file__).parent.parent.parent / "test-loop.flac"


@app.get("/turntable.flac")
async def stream_turntable(request: Request):
    """Serve FLAC file with debug logging"""

    if not AUDIO_FILE.exists():
        logger.error(f"Audio file not found: {AUDIO_FILE}")
        return {"error": f"Audio file not found: {AUDIO_FILE}"}

    file_size = AUDIO_FILE.stat().st_size

    # Log request details
    client_ip = request.client.host if request.client else "unknown"
    range_header = request.headers.get("range", "None")

    logger.info(f"")
    logger.info(f"📥 INCOMING REQUEST")
    logger.info(f"   Client: {client_ip}:{request.client.port if request.client else 'unknown'}")
    logger.info(f"   File: {AUDIO_FILE.name}")
    logger.info(f"   File size: {file_size} bytes")
    logger.info(f"   Range header: {range_header}")
    logger.info(f"   Request headers:")
    for key, value in request.headers.items():
        logger.info(f"     {key}: {value}")

    response = FileResponse(
        AUDIO_FILE,
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "bytes",
        },
    )

    logger.info(f"📤 RESPONSE")
    logger.info(f"   Media type: audio/flac")
    logger.info(f"   File size: {file_size} bytes")
    logger.info(f"   Accept-Ranges: bytes")

    return response


@app.get("/turntable.wav")
async def stream_turntable_wav(request: Request):
    """Serve WAV file (control test)"""

    wav_file = Path(__file__).parent.parent.parent / "test-loop.wav"

    if not wav_file.exists():
        logger.error(f"WAV file not found: {wav_file}")
        return {"error": f"WAV file not found: {wav_file}"}

    file_size = wav_file.stat().st_size

    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"")
    logger.info(f"📥 WAV REQUEST from {client_ip}")
    logger.info(f"   File size: {file_size} bytes")

    return FileResponse(
        wav_file,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "bytes",
        },
    )


@app.get("/")
async def root():
    return {
        "status": "TurnTabler Debug Streaming Server",
        "endpoints": {
            "flac": "/turntable.flac",
            "wav": "/turntable.wav",
        },
        "note": "Check server logs for detailed request/response debugging",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎵 Starting debug streaming server on http://0.0.0.0:8000")
    print("📻 FLAC endpoint: http://0.0.0.0:8000/turntable.flac")
    print("📻 WAV endpoint: http://0.0.0.0:8000/turntable.wav")
    print("📝 Check logs for detailed request information")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
