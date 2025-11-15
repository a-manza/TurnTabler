"""
FastAPI streaming server with ICY (SHOUTcast) metadata support.
Enables continuous radio-style streaming for Sonos with force_radio=True.
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pathlib import Path
import asyncio

app = FastAPI()

AUDIO_FILE = Path(__file__).parent.parent.parent / "test-loop.flac"
ICY_METAINT = 16000  # Send metadata every 16KB of audio


def encode_icy_metadata(title: str = "TurnTabler") -> bytes:
    """
    Encode metadata block in ICY format.

    ICY metadata format:
    - 1 byte: length (in 16-byte chunks)
    - N bytes: metadata string, padded to multiple of 16
    """
    # Standard ICY metadata format
    metadata_str = f"StreamTitle='{title}';StreamUrl='';"
    metadata_bytes = metadata_str.encode('utf-8')

    # Length in 16-byte chunks (rounded up)
    length = (len(metadata_bytes) + 15) // 16

    # Pad to 16-byte boundary
    padded = metadata_bytes.ljust(length * 16, b'\x00')

    # Return length byte + padded metadata
    return bytes([length]) + padded


@app.get("/turntable.flac")
async def stream_turntable(request: Request):
    """
    Stream FLAC file continuously with optional ICY metadata.

    If client requests ICY metadata (icy-metadata: 1 header),
    we send SHOUTcast protocol response for radio-style streaming.
    Otherwise, send plain HTTP file.
    """

    if not AUDIO_FILE.exists():
        return {"error": f"Audio file not found: {AUDIO_FILE}"}

    file_size = AUDIO_FILE.stat().st_size

    # Check if client wants ICY metadata (for force_radio=True)
    wants_icy = request.headers.get("icy-metadata", "0") == "1"

    if wants_icy:
        print(f"🎙️ ICY STREAM REQUEST - SHOUTcast metadata enabled")
        return await stream_with_icy_metadata()
    else:
        print(f"📁 PLAIN FILE REQUEST")
        return await stream_plain_file()


async def stream_plain_file():
    """Stream as plain HTTP file (for testing without force_radio)"""

    async def generate():
        chunk_size = 4096
        while True:
            try:
                with open(AUDIO_FILE, 'rb') as f:
                    while chunk := f.read(chunk_size):
                        yield chunk
                        await asyncio.sleep(0.001)
                print("♻️  Looping audio file (plain HTTP)")
            except Exception as e:
                print(f"❌ Error streaming: {e}")
                break

    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "bytes",
        },
    )


async def stream_with_icy_metadata():
    """Stream with ICY metadata for SHOUTcast protocol"""

    async def generate():
        metadata_block = encode_icy_metadata("TurnTabler")
        chunk_size = 4096
        bytes_sent = 0

        while True:
            try:
                with open(AUDIO_FILE, 'rb') as f:
                    while True:
                        audio_chunk = f.read(chunk_size)
                        if not audio_chunk:
                            break

                        # Track bytes sent for metadata insertion
                        bytes_to_send = len(audio_chunk)
                        bytes_sent += bytes_to_send

                        yield audio_chunk
                        await asyncio.sleep(0.001)

                        # Insert metadata block every ICY_METAINT bytes
                        if bytes_sent >= ICY_METAINT:
                            yield metadata_block
                            bytes_sent = 0

                # File ended, loop back
                print("♻️  Looping audio file (ICY metadata)")
                bytes_sent = 0  # Reset for next loop

            except Exception as e:
                print(f"❌ Error streaming: {e}")
                break

    # Return response with ICY headers
    # Note: FastAPI/Starlette may not preserve all headers perfectly,
    # but Sonos should accept audio/flac with icy-metaint
    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "icy-metaint": str(ICY_METAINT),
            "icy-name": "TurnTabler",
            "icy-genre": "Vinyl",
            "icy-br": "128",
            "Cache-Control": "no-cache",
            "Accept-Ranges": "none",
        },
    )


@app.get("/")
async def root():
    return {
        "status": "TurnTabler ICY Streaming Server",
        "endpoints": {
            "flac": "/turntable.flac",
        },
        "note": "Supports ICY metadata for force_radio=True",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎵 Starting ICY streaming server on http://0.0.0.0:8000")
    print("📻 Stream URL: http://0.0.0.0:8000/turntable.flac")
    print("🎙️  ICY metadata enabled for continuous streaming")
    uvicorn.run(app, host="0.0.0.0", port=8000)
