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

    This is a placeholder for the production USB audio capture.
    When integrated, this will use pyalsaaudio to capture from
    a Behringer UCA222 or similar USB audio interface.
    """

    def __init__(self, format: AudioFormat, device: str = 'default'):
        """
        Initialize USB audio source.

        Args:
            format: Audio format
            device: ALSA device name (e.g., 'hw:2,0')

        Raises:
            NotImplementedError: USB audio not yet implemented
        """
        raise NotImplementedError(
            "USB audio capture requires USB hardware and pyalsaaudio. "
            "Use SyntheticAudioSource or FileAudioSource for testing."
        )

    def read_chunk(self, num_frames: int) -> Optional[bytes]:
        """Not implemented."""
        raise NotImplementedError("USB audio not available")

    def close(self):
        """Close USB source."""
        pass
