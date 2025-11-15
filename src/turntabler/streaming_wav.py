"""
Continuous WAV streaming server for Sonos.

This module implements HTTP streaming of WAV audio using infinite headers
and chunked transfer encoding. Based on proven SWYH-RS architecture.

Supports both file-based streaming (POC) and real-time USB audio capture.
"""

import asyncio
import struct
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator, Protocol
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


@dataclass
class WAVFormat:
    """WAV audio format specification."""

    sample_rate: int = 48000
    channels: int = 2
    bits_per_sample: int = 16

    @property
    def byte_rate(self) -> int:
        """Bytes per second."""
        return self.sample_rate * self.channels * self.bits_per_sample // 8

    @property
    def block_align(self) -> int:
        """Bytes per sample frame."""
        return self.channels * self.bits_per_sample // 8

    @property
    def bandwidth_mbps(self) -> float:
        """Network bandwidth in Mbps."""
        return (self.byte_rate * 8) / 1_000_000


class AudioSource(Protocol):
    """Protocol for audio sources."""

    def read_chunk(self, size: int = 4096) -> Optional[bytes]:
        """
        Read audio chunk.

        Args:
            size: Maximum chunk size in bytes

        Returns:
            PCM audio data or None if exhausted
        """
        ...


class FileAudioSource:
    """
    Audio source that reads from a WAV file.

    Skips WAV header and loops indefinitely for continuous playback.
    Used for POC testing before USB audio integration.
    """

    def __init__(self, file_path: Path, loop: bool = True):
        """
        Initialize file audio source.

        Args:
            file_path: Path to WAV file
            loop: Loop file continuously (for POC testing)
        """
        self.file_path = file_path
        self.loop = loop
        self._file = None
        self._data_start = 0
        self._open()

    def _open(self):
        """Open WAV file and skip header."""
        self._file = open(self.file_path, 'rb')

        # Parse WAV header to find data chunk
        # Simple implementation - assumes standard WAV structure
        header = self._file.read(12)
        if not header.startswith(b'RIFF'):
            logger.warning(f"{self.file_path} not a WAV file, treating as raw PCM")
            self._file.seek(0)
            self._data_start = 0
            return

        # Find data chunk
        while True:
            chunk_header = self._file.read(8)
            if not chunk_header:
                break

            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

            if chunk_id == b'data':
                self._data_start = self._file.tell()
                logger.info(f"Found data chunk at offset {self._data_start}")
                break
            else:
                # Skip chunk
                self._file.seek(chunk_size, 1)

    def read_chunk(self, size: int = 4096) -> Optional[bytes]:
        """Read audio chunk from file."""
        if not self._file:
            return None

        data = self._file.read(size)

        if not data or len(data) < size:
            if self.loop:
                # Loop back to start of audio data
                self._file.seek(self._data_start)
                # Read remainder to fill chunk
                remainder = self._file.read(size - len(data))
                data = data + remainder
                logger.debug("Looped audio file")
            else:
                return None

        return data

    def close(self):
        """Close file."""
        if self._file:
            self._file.close()
            self._file = None


class USBAudioSourcePlaceholder:
    """
    Placeholder for USB audio source.

    Will be replaced with actual USBAudioCapture integration.
    For now, raises error with helpful message.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "USB audio capture not yet initialized. "
            "Run with --source file for POC testing."
        )

    def read_chunk(self, size: int = 4096) -> Optional[bytes]:
        """Not implemented."""
        raise NotImplementedError("USB audio not available")


def generate_wav_header(
    wav_format: WAVFormat,
    infinite: bool = True
) -> bytes:
    """
    Generate WAV file header.

    Args:
        wav_format: Audio format specification
        infinite: Use infinite size (0xFFFFFFFF) for streaming

    Returns:
        WAV header bytes (44 bytes)
    """
    # Use maximum value for infinite streams
    data_size = 0xFFFFFFFF if infinite else 0

    header = b''

    # RIFF header
    header += b'RIFF'
    header += struct.pack('<I', data_size)  # File size - 8
    header += b'WAVE'

    # fmt chunk
    header += b'fmt '
    header += struct.pack('<I', 16)  # fmt chunk size (PCM)
    header += struct.pack('<H', 1)   # Audio format (1 = PCM)
    header += struct.pack('<H', wav_format.channels)
    header += struct.pack('<I', wav_format.sample_rate)
    header += struct.pack('<I', wav_format.byte_rate)
    header += struct.pack('<H', wav_format.block_align)
    header += struct.pack('<H', wav_format.bits_per_sample)

    # data chunk
    header += b'data'
    header += struct.pack('<I', data_size)  # Data size

    return header


class WAVStreamingServer:
    """
    FastAPI server for streaming WAV audio to Sonos.

    Uses HTTP chunked transfer encoding with infinite WAV headers
    to enable continuous streaming without known duration.
    """

    def __init__(
        self,
        audio_source: AudioSource,
        wav_format: Optional[WAVFormat] = None,
        stream_name: str = "TurnTabler"
    ):
        """
        Initialize WAV streaming server.

        Args:
            audio_source: Audio source (file or USB)
            wav_format: WAV format specification
            stream_name: Display name for stream
        """
        self.audio_source = audio_source
        self.wav_format = wav_format or WAVFormat()
        self.stream_name = stream_name

        self.app = FastAPI(title="TurnTabler WAV Streaming Server")
        self._setup_routes()

        logger.info(f"WAV Streaming Server initialized")
        logger.info(f"Format: {self.wav_format.sample_rate}Hz, "
                   f"{self.wav_format.channels}ch, "
                   f"{self.wav_format.bits_per_sample}-bit")
        logger.info(f"Bandwidth: {self.wav_format.bandwidth_mbps:.2f} Mbps")

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Server info endpoint."""
            return {
                "status": "TurnTabler WAV Streaming Server",
                "stream_url": "/stream.wav",
                "format": {
                    "sample_rate": self.wav_format.sample_rate,
                    "channels": self.wav_format.channels,
                    "bits_per_sample": self.wav_format.bits_per_sample,
                    "bandwidth_mbps": round(self.wav_format.bandwidth_mbps, 2)
                },
                "stream_name": self.stream_name
            }

        @self.app.get("/stream.wav")
        async def stream_wav(request: Request):
            """
            WAV streaming endpoint.

            Returns continuous WAV stream with infinite header.
            """
            client_addr = request.client.host if request.client else "unknown"
            logger.info(f"Stream request from {client_addr}")

            return StreamingResponse(
                self._generate_stream(),
                media_type="audio/wav",
                headers={
                    "icy-name": self.stream_name,
                    "Cache-Control": "no-cache, no-store",
                    # Chunked encoding (no Content-Length header)
                }
            )

    async def _generate_stream(self) -> AsyncGenerator[bytes, None]:
        """
        Generate WAV stream.

        Yields:
            WAV header followed by continuous PCM data chunks
        """
        # Send WAV header first
        header = generate_wav_header(self.wav_format, infinite=True)
        yield header
        logger.info("WAV header sent (infinite size)")

        # Stream audio data
        chunk_count = 0
        total_bytes = 0

        try:
            while True:
                # Read audio chunk from source
                chunk = self.audio_source.read_chunk(4096)

                if chunk is None:
                    logger.info("Audio source exhausted")
                    break

                yield chunk

                chunk_count += 1
                total_bytes += len(chunk)

                # Periodic logging
                if chunk_count % 1000 == 0:
                    mb_sent = total_bytes / 1_000_000
                    seconds = total_bytes / self.wav_format.byte_rate
                    logger.debug(
                        f"Streamed {chunk_count} chunks "
                        f"({mb_sent:.1f}MB, {seconds:.1f}s)"
                    )

                # Small async yield to prevent blocking
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

        finally:
            logger.info(f"Stream ended: {chunk_count} chunks, "
                       f"{total_bytes/1_000_000:.1f}MB")


def create_app(
    audio_source: AudioSource,
    wav_format: Optional[WAVFormat] = None,
    stream_name: str = "TurnTabler"
) -> FastAPI:
    """
    Create FastAPI application for WAV streaming.

    Args:
        audio_source: Audio source (file or USB)
        wav_format: WAV format specification
        stream_name: Display name for stream

    Returns:
        Configured FastAPI app
    """
    server = WAVStreamingServer(audio_source, wav_format, stream_name)
    return server.app


# Convenience function for CLI
def run_server(
    audio_source: AudioSource,
    host: str = "0.0.0.0",
    port: int = 5901,
    wav_format: Optional[WAVFormat] = None,
    stream_name: str = "TurnTabler"
):
    """
    Run WAV streaming server.

    Args:
        audio_source: Audio source (file or USB)
        host: Bind address
        port: Bind port
        wav_format: WAV format specification
        stream_name: Display name for stream
    """
    import uvicorn

    app = create_app(audio_source, wav_format, stream_name)

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Stream URL: http://{host}:{port}/stream.wav")

    uvicorn.run(app, host=host, port=port, log_level="info")


# Standalone testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python -m turntabler.streaming_wav <wav_file>")
        print("\nExample:")
        print("  python -m turntabler.streaming_wav test-loop.wav")
        sys.exit(1)

    wav_file = Path(sys.argv[1])

    if not wav_file.exists():
        print(f"Error: File not found: {wav_file}")
        sys.exit(1)

    print(f"Starting WAV streaming server")
    print(f"Source: {wav_file}")
    print(f"Format: 48kHz, 2ch, 16-bit (1.5 Mbps)")
    print(f"Stream URL: http://0.0.0.0:5901/stream.wav")
    print(f"\nPress Ctrl+C to stop\n")

    audio_source = FileAudioSource(wav_file, loop=True)

    try:
        run_server(audio_source)
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        audio_source.close()
