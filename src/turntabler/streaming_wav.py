"""
Continuous WAV streaming server for Sonos.

This module implements HTTP streaming of WAV audio using infinite headers
and chunked transfer encoding. Based on proven SWYH-RS architecture.

Supports both file-based streaming (POC) and real-time USB audio capture.
"""

import asyncio
import logging
import struct
import threading
import time
from collections import deque
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from turntabler.audio_source import AudioFormat
from turntabler.diagnostics import StreamingDiagnostics

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
        diagnostics: Optional[StreamingDiagnostics] = None,
        buffer_size: int = 12,  # ~500ms at 42.7ms per chunk
    ):
        """
        Initialize WAV streaming server.

        Args:
            audio_source: Audio source (file or USB)
            wav_format: WAV format specification
            stream_name: Display name for stream
            diagnostics: Optional diagnostics collector for performance metrics
            buffer_size: Number of chunks to buffer (default 12 = ~500ms)
        """
        self.audio_source = audio_source
        self.wav_format = wav_format or AudioFormat()
        self.stream_name = stream_name
        self.diagnostics = diagnostics
        self.buffer_size = buffer_size

        # Producer-consumer buffer
        self._buffer: deque = deque(maxlen=buffer_size * 2)  # Allow some headroom
        self._buffer_lock = threading.Lock()
        self._producer_thread: Optional[threading.Thread] = None
        self._stop_producer = threading.Event()
        self._buffer_ready = threading.Event()

        self.app = FastAPI(title="TurnTabler WAV Streaming Server")
        self._setup_routes()

        logger.info("WAV Streaming Server initialized")
        logger.info(
            f"Format: {self.wav_format.sample_rate}Hz, "
            f"{self.wav_format.channels}ch, "
            f"{self.wav_format.bits_per_sample}-bit"
        )
        logger.info(f"Bandwidth: {self.wav_format.bandwidth_mbps:.2f} Mbps")
        logger.info(f"Buffer: {buffer_size} chunks (~{buffer_size * 42.7:.0f}ms)")

    def start_producer(self) -> bool:
        """
        Start the producer thread that reads from audio source into buffer.

        Returns:
            True if producer started successfully
        """
        if self._producer_thread and self._producer_thread.is_alive():
            logger.warning("Producer already running")
            return True

        self._stop_producer.clear()
        self._buffer_ready.clear()

        self._producer_thread = threading.Thread(
            target=self._producer_loop,
            name="audio-producer",
            daemon=True
        )
        self._producer_thread.start()
        logger.info("Started audio producer thread")
        return True

    def stop_producer(self):
        """Stop the producer thread."""
        self._stop_producer.set()
        if self._producer_thread:
            self._producer_thread.join(timeout=2.0)
            logger.info("Stopped audio producer thread")

    def _producer_loop(self):
        """Producer thread loop - reads audio and fills buffer."""
        logger.info("Producer loop started")

        while not self._stop_producer.is_set():
            # Read chunk from audio source
            read_start = time.time()
            chunk = self.audio_source.read_chunk(8192)
            read_latency_ms = (time.time() - read_start) * 1000

            if chunk is None:
                logger.info("Audio source exhausted in producer")
                break

            # Record read diagnostics
            if self.diagnostics:
                self.diagnostics.record_chunk_read(len(chunk), read_latency_ms)

            # Add to buffer
            with self._buffer_lock:
                self._buffer.append(chunk)
                buffer_len = len(self._buffer)

            # Signal that buffer has data (for initial pre-fill)
            if buffer_len >= self.buffer_size and not self._buffer_ready.is_set():
                self._buffer_ready.set()
                logger.info(f"Buffer pre-filled with {buffer_len} chunks")

        logger.info("Producer loop ended")

    def prefill_buffer(self, timeout: float = 5.0) -> bool:
        """
        Wait for buffer to be pre-filled.

        Call this before telling Sonos to play to ensure immediate data.

        Args:
            timeout: Maximum seconds to wait for buffer fill

        Returns:
            True if buffer filled, False if timeout
        """
        if not self._producer_thread or not self._producer_thread.is_alive():
            logger.error("Producer not running - call start_producer() first")
            return False

        logger.info(f"Waiting for buffer to fill ({self.buffer_size} chunks)...")
        if self._buffer_ready.wait(timeout=timeout):
            with self._buffer_lock:
                logger.info(f"Buffer ready with {len(self._buffer)} chunks")
            return True
        else:
            logger.error(f"Buffer fill timeout after {timeout}s")
            return False

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
            WAV header followed by continuous PCM data chunks from buffer
        """
        # Send WAV header first
        header = generate_wav_header(self.wav_format, infinite=True)
        yield header
        logger.info("WAV header sent (infinite size)")

        # Stream audio data from buffer
        chunk_count = 0
        total_bytes = 0

        try:
            while True:
                yield_start = time.time()

                # Get chunk from buffer
                chunk = await asyncio.to_thread(self._get_from_buffer)

                if chunk is None:
                    logger.info("Buffer exhausted - producer stopped")
                    break

                yield chunk
                yield_latency_ms = (time.time() - yield_start) * 1000

                # Record diagnostics
                if self.diagnostics:
                    self.diagnostics.record_yield(yield_latency_ms)

                chunk_count += 1
                total_bytes += len(chunk)

                # Periodic logging
                if chunk_count % 1000 == 0:
                    mb_sent = total_bytes / 1_000_000
                    seconds = total_bytes / self.wav_format.byte_rate
                    with self._buffer_lock:
                        buf_len = len(self._buffer)
                    logger.debug(
                        f"Streamed {chunk_count} chunks "
                        f"({mb_sent:.1f}MB, {seconds:.1f}s) buffer={buf_len}"
                    )

        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

        finally:
            logger.info(
                f"Stream ended: {chunk_count} chunks, {total_bytes / 1_000_000:.1f}MB"
            )

    def _get_from_buffer(self) -> Optional[bytes]:
        """
        Get a chunk from the buffer, waiting if necessary.

        Returns:
            Audio chunk bytes, or None if producer stopped and buffer empty
        """
        # Wait for data with timeout to allow checking producer status
        max_wait = 0.1  # 100ms timeout per iteration
        waited = 0.0
        max_total_wait = 2.0  # Give up after 2 seconds

        while waited < max_total_wait:
            with self._buffer_lock:
                if self._buffer:
                    chunk = self._buffer.popleft()
                    buffer_len = len(self._buffer)

                    # Record buffer occupancy
                    if self.diagnostics:
                        self.diagnostics.record_buffer_occupancy(buffer_len)

                    return chunk

            # Buffer empty - check if producer stopped
            if self._stop_producer.is_set():
                return None

            # Wait a bit for producer to add data
            time.sleep(max_wait)
            waited += max_wait

        # Timeout - producer might be stuck
        logger.warning(f"Buffer underrun - waited {waited:.1f}s for data")
        return None
