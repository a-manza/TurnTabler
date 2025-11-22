"""
Continuous WAV streaming server for Sonos.

This module implements HTTP streaming of WAV audio using infinite headers
and chunked transfer encoding. Based on proven SWYH-RS architecture.

Supports both file-based streaming (POC) and real-time USB audio capture.
"""

import asyncio
import logging
import struct
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from turntabler.audio_source import AudioFormat

logger = logging.getLogger(__name__)


def generate_wav_header(wav_format: AudioFormat, infinite: bool = True) -> bytes:
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

    header = b""

    # RIFF header
    header += b"RIFF"
    header += struct.pack("<I", data_size)  # File size - 8
    header += b"WAVE"

    # fmt chunk
    header += b"fmt "
    header += struct.pack("<I", 16)  # fmt chunk size (PCM)
    header += struct.pack("<H", 1)  # Audio format (1 = PCM)
    header += struct.pack("<H", wav_format.channels)
    header += struct.pack("<I", wav_format.sample_rate)
    header += struct.pack("<I", wav_format.byte_rate)
    header += struct.pack("<H", wav_format.block_align)
    header += struct.pack("<H", wav_format.bits_per_sample)

    # data chunk
    header += b"data"
    header += struct.pack("<I", data_size)  # Data size

    return header


class WAVStreamingServer:
    """
    FastAPI server for streaming WAV audio to Sonos.

    Uses HTTP chunked transfer encoding with infinite WAV headers
    to enable continuous streaming without known duration.
    """

    def __init__(
        self,
        audio_source: Any,
        wav_format: Optional[AudioFormat] = None,
        stream_name: str = "TurnTabler",
    ):
        """
        Initialize WAV streaming server.

        Args:
            audio_source: Audio source (file or USB)
            wav_format: WAV format specification
            stream_name: Display name for stream
        """
        self.audio_source = audio_source
        self.wav_format = wav_format or AudioFormat()
        self.stream_name = stream_name

        self.app = FastAPI(title="TurnTabler WAV Streaming Server")
        self._setup_routes()

        logger.info("WAV Streaming Server initialized")
        logger.info(
            f"Format: {self.wav_format.sample_rate}Hz, "
            f"{self.wav_format.channels}ch, "
            f"{self.wav_format.bits_per_sample}-bit"
        )
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
                    "bandwidth_mbps": round(self.wav_format.bandwidth_mbps, 2),
                },
                "stream_name": self.stream_name,
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
                },
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
                # Read audio chunk from source (in thread to avoid blocking event loop)
                chunk = await asyncio.to_thread(self.audio_source.read_chunk, 4096)

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

        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

        finally:
            logger.info(
                f"Stream ended: {chunk_count} chunks, {total_bytes / 1_000_000:.1f}MB"
            )
