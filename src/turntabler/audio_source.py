"""
Audio source abstractions for TurnTabler.

Defines the interface and implementations for audio sources:
- Synthetic (for testing/POC)
- File-based (for POC with WAV files)
- USB-based (for production with turntable)
"""

import struct
import math
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class AudioFormat:
    """Audio format specification."""
    sample_rate: int = 48000
    channels: int = 2
    bits_per_sample: int = 16

    @property
    def bytes_per_sample(self) -> int:
        """Bytes per audio sample (all channels)."""
        return self.channels * self.bits_per_sample // 8

    @property
    def byte_rate(self) -> int:
        """Bytes per second."""
        return self.sample_rate * self.bytes_per_sample

    @property
    def block_align(self) -> int:
        """Bytes per sample frame (all channels)."""
        return self.bytes_per_sample

    @property
    def bandwidth_mbps(self) -> float:
        """Network bandwidth in Mbps."""
        return (self.byte_rate * 8) / 1_000_000


class AudioSource(ABC):
    """Base class for audio sources."""

    @abstractmethod
    def read_chunk(self, num_frames: int) -> Optional[bytes]:
        """
        Read audio chunk.

        Args:
            num_frames: Number of audio frames to read

        Returns:
            PCM audio data or None if exhausted
        """
        pass

    @abstractmethod
    def close(self):
        """Close audio source."""
        pass


class SyntheticAudioSource(AudioSource):
    """
    Generate synthetic audio for testing.

    Produces a musical note or sweep pattern in real-time.
    Simulates continuous audio capture like a turntable would produce.
    """

    def __init__(
        self,
        format: AudioFormat,
        frequency: float = 440.0,
        amplitude: float = 0.5
    ):
        """
        Initialize synthetic audio source.

        Args:
            format: Audio format
            frequency: Frequency in Hz (440 = A4 concert pitch)
            amplitude: Amplitude 0.0-1.0
        """
        self.format = format
        self.frequency = frequency
        self.amplitude = amplitude
        self.sample_count = 0

    def read_chunk(self, num_frames: int) -> Optional[bytes]:
        """Generate synthetic audio chunk."""
        if num_frames <= 0:
            return None

        audio_data = bytearray()

        for i in range(num_frames):
            # Generate sine wave sample
            t = (self.sample_count + i) / self.format.sample_rate
            sample_value = math.sin(2 * math.pi * self.frequency * t)
            sample_value *= self.amplitude

            # Convert to PCM (16-bit signed little-endian)
            if self.format.bits_per_sample == 16:
                # Scale to 16-bit range (-32768 to 32767)
                pcm_value = int(sample_value * 32767)
                pcm_value = max(-32768, min(32767, pcm_value))

                # Convert to little-endian bytes
                for _ in range(self.format.channels):
                    audio_data.extend(struct.pack('<h', pcm_value))
            else:
                raise ValueError(
                    f"Unsupported bit depth: {self.format.bits_per_sample}"
                )

        self.sample_count += num_frames
        return bytes(audio_data)

    def close(self):
        """No-op for synthetic source."""
        pass


class FileAudioSource(AudioSource):
    """
    Read audio from a WAV file.

    Loops indefinitely for continuous playback testing.
    """

    def __init__(self, file_path: str, format: AudioFormat):
        """
        Initialize file audio source.

        Args:
            file_path: Path to WAV file
            format: Audio format
        """
        self.file_path = file_path
        self.format = format
        self._file = None
        self._data_start = 0
        self._open()

    def _open(self):
        """Open WAV file and locate data chunk."""
        self._file = open(self.file_path, 'rb')

        # Parse WAV header
        header = self._file.read(12)
        if not header.startswith(b'RIFF'):
            # Assume raw PCM
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
                break
            else:
                self._file.seek(chunk_size, 1)

    def read_chunk(self, num_frames: int) -> Optional[bytes]:
        """Read audio chunk from file."""
        if not self._file:
            return None

        chunk_size = num_frames * self.format.bytes_per_sample
        data = self._file.read(chunk_size)

        if not data:
            # Loop back to start
            self._file.seek(self._data_start)
            data = self._file.read(chunk_size)

        return data if data else None

    def close(self):
        """Close file."""
        if self._file:
            self._file.close()
            self._file = None


class USBAudioSource(AudioSource):
    """
    Capture audio from USB interface.

    Production implementation for real-time audio capture from USB audio
    interfaces like the Behringer UCA202/UCA222.

    Requires: pyalsaaudio (install with: uv pip install -e ".[usb]")
    """

    def __init__(self, format: AudioFormat, device: Optional[str] = None):
        """
        Initialize USB audio source.

        Args:
            format: Audio format specification (48kHz, 2ch, 16-bit recommended)
            device: ALSA device name (e.g., 'hw:CARD=CODEC,DEV=0').
                   If None, auto-detects first USB audio device.

        Raises:
            ImportError: If pyalsaaudio not installed
            RuntimeError: If no USB audio device found or failed to open

        Example:
            # Auto-detect UCA202
            source = USBAudioSource(AudioFormat())

            # Specify device manually
            source = USBAudioSource(AudioFormat(), device='hw:CARD=CODEC,DEV=0')
        """
        import logging

        # Check pyalsaaudio availability
        try:
            from .usb_audio_capture import USBAudioCapture, CaptureConfig, SampleFormat
            from .usb_audio import detect_usb_audio_device
        except ImportError:
            raise ImportError(
                "USB audio requires pyalsaaudio. "
                "Install with: uv pip install -e \".[usb]\""
            )

        self.format = format
        self.logger = logging.getLogger(__name__)

        # Auto-detect device if not specified
        if device is None:
            self.logger.info("Auto-detecting USB audio device...")
            device = detect_usb_audio_device()
            if device is None:
                raise RuntimeError(
                    "No USB audio device found. "
                    "Ensure USB interface is connected and recognized by ALSA. "
                    "Troubleshoot with: arecord -l"
                )
            self.logger.info(f"Auto-detected: {device}")

        # Validate format compatibility
        if format.bits_per_sample != 16:
            self.logger.warning(
                f"UCA202/UCA222 only supports 16-bit audio. "
                f"Requested {format.bits_per_sample}-bit will use 16-bit."
            )

        # Create capture configuration optimized for UCA202/UCA222
        config = CaptureConfig(
            device=device,
            sample_rate=format.sample_rate,
            channels=format.channels,
            sample_format=SampleFormat.S16_LE,  # UCA202 native format
            period_size=1024,  # ~21ms latency (appropriate for vinyl)
            periods=3          # USB audio recommended buffer
        )

        # Initialize capture
        self.logger.info(f"Opening USB audio device: {device}")
        self.capture = USBAudioCapture(config)

        if not self.capture.open():
            raise RuntimeError(
                f"Failed to open USB audio device: {device}\n"
                f"Possible causes:\n"
                f"  - Device in use by another application\n"
                f"  - Insufficient permissions (run: sudo usermod -a -G audio $USER)\n"
                f"  - ALSA configuration issue"
            )

        # Start capture stream generator
        self._stream = self.capture.capture_stream()

        self.logger.info(
            f"USB audio source ready: {device} "
            f"({format.sample_rate}Hz, {format.channels}ch, {format.bits_per_sample}-bit)"
        )

    def read_chunk(self, num_frames: int) -> Optional[bytes]:
        """
        Read audio chunk from USB interface.

        Args:
            num_frames: Number of frames requested (actual size may vary
                       based on ALSA period size)

        Returns:
            PCM audio data (bytes) or None if stream ended or error occurred
        """
        if self._stream is None:
            return None

        try:
            # Pull next chunk from capture stream
            return next(self._stream)
        except StopIteration:
            self.logger.info("USB capture stream ended")
            return None
        except Exception as e:
            self.logger.error(f"USB audio capture error: {e}")
            return None

    def close(self):
        """Close USB audio capture and release ALSA resources."""
        if hasattr(self, '_stream') and self._stream:
            try:
                self.capture.stop()
                self.logger.info("Stopped USB capture stream")
            except Exception as e:
                self.logger.warning(f"Error stopping capture: {e}")
            finally:
                self._stream = None

        if hasattr(self, 'capture') and self.capture:
            try:
                self.capture.close()
                self.logger.info("USB audio source closed")
            except Exception as e:
                self.logger.warning(f"Error closing capture: {e}")
