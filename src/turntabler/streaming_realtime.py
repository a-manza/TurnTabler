"""
Real-time chunk streaming server.

Simulates continuous USB audio capture by streaming pre-encoded FLAC chunks.
Each chunk is a complete, valid FLAC file.
Chunks cycle continuously, simulating infinite audio stream.

This mimics what the turntable will do:
USB Audio → Capture → Encode → Stream chunks to Sonos
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pathlib import Path
import asyncio
import time

app = FastAPI()

# Load pre-generated FLAC chunks
CHUNKS_DIR = Path(__file__).parent / "chunks"
CHUNKS = sorted(CHUNKS_DIR.glob("chunk_*.flac"))

if not CHUNKS:
    print("⚠️  Warning: No FLAC chunks found in chunks/")
    print(f"   Run: python generate_flac_chunks.py")


@app.get("/turntable.flac")
async def stream_turntable():
    """
    Stream FLAC chunks continuously.

    Each chunk is a complete FLAC file.
    Chunks cycle through indefinitely, simulating continuous USB capture.

    No Content-Length header → HTTP chunked transfer encoding
    No force_radio → Plain HTTP stream (Sonos accepts as continuous)
    """

    async def generate():
        chunk_index = 0
        start_time = time.time()
        bytes_sent = 0

        print(f"🎵 Starting continuous chunk stream")
        print(f"   Chunks: {len(CHUNKS)}")
        print(f"   Duration: {len(CHUNKS) * 3}s per cycle")

        while True:
            # Get next chunk (cycle through all chunks)
            chunk_num = chunk_index % len(CHUNKS)
            chunk_file = CHUNKS[chunk_num]

            try:
                chunk_data = chunk_file.read_bytes()
                bytes_sent += len(chunk_data)

                # Log chunk delivery
                elapsed = time.time() - start_time
                chunk_time_sec = elapsed
                print(
                    f"  [{chunk_index:3d}] Chunk {chunk_num:2d} ({chunk_file.name}) "
                    f"→ {len(chunk_data)/1024:.1f}KB | "
                    f"Total: {bytes_sent/1024/1024:.1f}MB ({chunk_time_sec:.1f}s)"
                )

                yield chunk_data
                chunk_index += 1

                # Small delay between chunks (0.1s) to simulate processing
                # In real turntable, this would be the time to encode the chunk
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"❌ Error reading chunk: {e}")
                break

    return StreamingResponse(
        generate(),
        media_type="audio/flac",
        headers={
            "Cache-Control": "no-cache",
            "Accept-Ranges": "none",
            # NO Content-Length header → HTTP chunked encoding
            # NO icy-metadata → plain HTTP stream
        },
    )


@app.get("/")
async def root():
    return {
        "status": "TurnTabler Real-Time Chunk Streaming Server",
        "stream_url": "/turntable.flac",
        "chunks_loaded": len(CHUNKS),
        "note": "Simulates continuous USB audio by cycling through FLAC chunks",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎵 Starting real-time chunk streaming server")
    print(f"📁 Chunks directory: {CHUNKS_DIR}")
    print(f"📊 Loaded {len(CHUNKS)} chunks ({len(CHUNKS)*3}s per cycle)")
    print("📻 Stream URL: http://0.0.0.0:8000/turntable.flac")
    print("\n⚠️  NOTE: Use control.py WITHOUT force_radio for this server")
    print("   (force_radio expects ICY metadata, not needed for chunked HTTP)\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
