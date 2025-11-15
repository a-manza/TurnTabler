"""
USB Audio capture implementation using ALSA.

This module provides a production-ready audio capture implementation using
pyalsaaudio. It supports real-time audio capture with configurable quality,
latency, and error handling.

Typical usage:
    >>> from turntabler.usb_audio import detect_usb_audio_device
    >>> from turntabler.usb_audio_capture import USBAudioCapture, CaptureConfig, SampleFormat
    >>>
    >>> # Detect device
    >>> device = detect_usb_audio_device()
    >>>
    >>> # Configure capture
    >>> config = CaptureConfig(
    ...     device=device,
    ...     sample_rate=48000,
    ...     channels=2,
    ...     sample_format=SampleFormat.S16_LE
    ... )
    >>>
    >>> # Capture audio
    >>> capture = USBAudioCapture(config)
    >>> if capture.open():
    ...     for chunk in capture.capture_stream(duration_seconds=10):
    ...         # Process audio chunks
    ...         pass
    ...     capture.close()
"""

import alsaaudio
import time
import logging
from typing import Optional, Callable, Generator
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class SampleFormat(Enum):
    """
    Supported PCM sample formats.

    These formats represent different bit depths and encoding types for
    audio samples. Choose based on your USB audio interface capabilities
    and quality requirements.
    """
    S16_LE = alsaaudio.PCM_FORMAT_S16_LE      # 16-bit signed little-endian (most compatible)
    S24_3LE = alsaaudio.PCM_FORMAT_S24_3LE    # 24-bit signed little-endian (3 bytes per sample)
    S32_LE = alsaaudio.PCM_FORMAT_S32_LE      # 32-bit signed little-endian


@dataclass
class CaptureConfig:
    """
    Configuration for audio capture.

    This dataclass encapsulates all parameters needed to configure ALSA
    audio capture. Default values are optimized for vinyl streaming with
    USB audio interfaces on Raspberry Pi.

    Attributes:
        device: ALSA device name (e.g., 'hw:CARD=UCA222,DEV=0')
        sample_rate: Samples per second (Hz). 48000 recommended for vinyl.
        channels: Number of audio channels (1=mono, 2=stereo)
        sample_format: Bit depth and encoding (see SampleFormat enum)
        period_size: Frames per period. Affects latency and reliability.
                    1024 recommended for USB audio (balance of latency/reliability)
        periods: Number of periods in buffer. 3 recommended for USB devices.

    Example:
        >>> config = CaptureConfig(
        ...     device='hw:1,0',
        ...     sample_rate=48000,
        ...     period_size=1024,
        ...     periods=3
        ... )
        >>> print(f"Latency: {config.latency_ms:.2f}ms")
    """
    device: str = 'default'
    sample_rate: int = 48000
    channels: int = 2
    sample_format: SampleFormat = SampleFormat.S16_LE
    period_size: int = 1024
    periods: int = 3

    @property
    def latency_ms(self) -> float:
        """
        Calculate approximate latency in milliseconds.

        Latency is determined by the period size and sample rate.
        Lower period size = lower latency, but higher CPU usage and
        risk of buffer overruns.

        Returns:
            Latency in milliseconds

        Example:
            >>> config = CaptureConfig(period_size=1024, sample_rate=48000)
            >>> print(config.latency_ms)  # 21.33ms
        """
        return (self.period_size / self.sample_rate) * 1000

    @property
    def bytes_per_sample(self) -> int:
        """
        Bytes per sample based on format.

        Returns:
            Number of bytes per sample (2 for 16-bit, 3 for 24-bit, 4 for 32-bit)
        """
        if self.sample_format == SampleFormat.S16_LE:
            return 2
        elif self.sample_format == SampleFormat.S24_3LE:
            return 3
        elif self.sample_format == SampleFormat.S32_LE:
            return 4
        return 2  # default

    @property
    def bytes_per_frame(self) -> int:
        """
        Bytes per frame (all channels).

        A frame contains one sample for each channel.

        Returns:
            bytes_per_sample * channels
        """
        return self.bytes_per_sample * self.channels

    @property
    def period_bytes(self) -> int:
        """
        Expected bytes per period.

        Returns:
            Number of bytes expected in each captured period
        """
        return self.period_size * self.bytes_per_frame

    @property
    def bit_depth(self) -> int:
        """
        Bit depth of samples.

        Returns:
            Bit depth (16, 24, or 32)
        """
        if self.sample_format == SampleFormat.S16_LE:
            return 16
        elif self.sample_format == SampleFormat.S24_3LE:
            return 24
        elif self.sample_format == SampleFormat.S32_LE:
            return 32
        return 16  # default

    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"CaptureConfig(device={self.device}, "
            f"{self.sample_rate}Hz, {self.channels}ch, "
            f"{self.bit_depth}bit, period={self.period_size}, "
            f"latency={self.latency_ms:.1f}ms)"
        )


class CaptureError(Exception):
    """Exception raised for capture-related errors."""
    pass


class USBAudioCapture:
    """
    USB Audio capture using ALSA.

    This class provides a robust interface for capturing audio from USB
    audio interfaces using ALSA. It includes error handling, buffer
    management, and recovery from common USB audio issues.

    Example:
        >>> config = CaptureConfig(device='hw:1,0')
        >>> capture = USBAudioCapture(config)
        >>> if capture.open():
        ...     try:
        ...         for chunk in capture.capture_stream(duration_seconds=5):
        ...             print(f"Captured {len(chunk)} bytes")
        ...     finally:
        ...         capture.close()
    """

    def __init__(self, config: CaptureConfig):
        """
        Initialize USB audio capture.

        Args:
            config: CaptureConfig object with capture parameters
        """
        self.config = config
        self.pcm: Optional[alsaaudio.PCM] = None
        self.is_capturing = False
        self._frames_captured = 0
        self._overruns = 0

        logger.info(f"USB Audio Capture initialized: {config}")

    def open(self) -> bool:
        """
        Open ALSA device for capture.

        Attempts to open the configured ALSA device with the specified
        parameters. If successful, the device is ready for capture.

        Returns:
            True if successful, False otherwise

        Example:
            >>> capture = USBAudioCapture(config)
            >>> if not capture.open():
            ...     print("Failed to open device")
        """
        try:
            self.pcm = alsaaudio.PCM(
                type=alsaaudio.PCM_CAPTURE,
                mode=alsaaudio.PCM_NONBLOCK,
                rate=self.config.sample_rate,
                channels=self.config.channels,
                format=self.config.sample_format.value,
                periodsize=self.config.period_size,
                device=self.config.device
            )

            logger.info(f"Opened ALSA device: {self.config.device}")
            return True

        except alsaaudio.ALSAAudioError as e:
            logger.error(f"Failed to open ALSA device '{self.config.device}': {e}")
            logger.error("Check that:")
            logger.error("  1. Device is connected and powered")
            logger.error("  2. Device name is correct (use 'arecord -l' to list)")
            logger.error("  3. User has permissions (add to 'audio' group)")
            return False

    def close(self):
        """
        Close ALSA device.

        Always call this method when done capturing to release the device
        and allow other applications to use it.
        """
        if self.pcm:
            self.pcm.close()
            self.pcm = None
            logger.info("Closed ALSA device")

            if self._overruns > 0:
                logger.warning(
                    f"Capture session had {self._overruns} buffer overrun(s). "
                    f"Consider increasing period_size or periods."
                )

    def capture_stream(
        self,
        callback: Optional[Callable[[bytes], None]] = None,
        duration_seconds: Optional[float] = None
    ) -> Generator[bytes, None, None]:
        """
        Capture audio stream as generator.

        This generator yields audio data chunks as they are captured from
        the device. Each chunk contains approximately period_size frames
        of audio data.

        Args:
            callback: Optional callback function called with each audio chunk.
                     Useful for processing audio while capturing (e.g., writing to file)
            duration_seconds: Optional duration limit in seconds. If None, captures
                            indefinitely (until stop() is called or KeyboardInterrupt)

        Yields:
            Audio data as bytes (raw PCM audio)

        Raises:
            CaptureError: If device not opened or critical capture error occurs

        Example:
            >>> def save_chunk(data):
            ...     with open('output.raw', 'ab') as f:
            ...         f.write(data)
            >>>
            >>> for chunk in capture.capture_stream(callback=save_chunk, duration_seconds=10):
            ...     print(f"Captured {len(chunk)} bytes")
        """
        if not self.pcm:
            raise CaptureError("Device not opened. Call open() first.")

        self.is_capturing = True
        start_time = time.time()
        self._frames_captured = 0
        self._overruns = 0

        logger.info("Starting audio capture...")
        if duration_seconds:
            logger.info(f"Duration limit: {duration_seconds}s")

        try:
            while self.is_capturing:
                # Check duration limit
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"Reached duration limit: {duration_seconds}s")
                    break

                # Read audio data
                length, data = self.pcm.read()

                if length > 0:
                    # Successfully read data
                    self._frames_captured += length

                    # Call callback if provided
                    if callback:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                    yield data

                elif length == 0:
                    # No data available yet (non-blocking mode)
                    # Sleep briefly to prevent busy-wait CPU spinning
                    time.sleep(0.001)  # 1ms

                elif length == -alsaaudio.EPIPE:
                    # Buffer overrun - we're not reading fast enough
                    self._overruns += 1
                    logger.warning(
                        f"Buffer overrun detected (EPIPE) - overrun #{self._overruns}. "
                        f"Consider increasing period_size or periods."
                    )
                    # Continue capturing (ALSA recovers automatically)

                elif length < 0:
                    # Other error
                    logger.error(f"Capture error: {length}")
                    raise CaptureError(f"ALSA capture error: {length}")

        except KeyboardInterrupt:
            logger.info("Capture interrupted by user (Ctrl+C)")

        finally:
            self.is_capturing = False
            elapsed = time.time() - start_time
            logger.info(
                f"Capture stopped. "
                f"Duration: {elapsed:.2f}s, "
                f"Frames: {self._frames_captured}, "
                f"Overruns: {self._overruns}"
            )

    def stop(self):
        """
        Stop capture stream.

        Signals the capture_stream generator to stop. The generator will
        complete its current iteration and then exit.

        Example:
            >>> import threading
            >>> capture = USBAudioCapture(config)
            >>> capture.open()
            >>>
            >>> # Start capture in background
            >>> def capture_thread():
            ...     for chunk in capture.capture_stream():
            ...         process(chunk)
            >>>
            >>> thread = threading.Thread(target=capture_thread)
            >>> thread.start()
            >>>
            >>> # Stop after 10 seconds
            >>> time.sleep(10)
            >>> capture.stop()
            >>> thread.join()
            >>> capture.close()
        """
        if self.is_capturing:
            logger.info("Stopping capture...")
            self.is_capturing = False

    @property
    def frames_captured(self) -> int:
        """Number of frames captured in current or last session."""
        return self._frames_captured

    @property
    def overruns(self) -> int:
        """Number of buffer overruns in current or last session."""
        return self._overruns


# Example usage and testing
if __name__ == '__main__':
    import sys
    from turntabler.usb_audio import detect_usb_audio_device

    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("USB Audio Capture Test")
    print("=" * 60)
    print()

    # Detect USB audio device
    print("Detecting USB audio device...")
    device = detect_usb_audio_device()

    if not device:
        print("ERROR: No USB audio device found")
        print()
        print("Make sure:")
        print("  1. USB audio interface is connected")
        print("  2. Device is powered on (if external power required)")
        print("  3. User has permissions (run: sudo usermod -a -G audio $USER)")
        print()
        print("To list devices manually, run: arecord -l")
        sys.exit(1)

    print(f"Using device: {device}")
    print()

    # Create capture configuration
    config = CaptureConfig(
        device=device,
        sample_rate=48000,
        channels=2,
        sample_format=SampleFormat.S16_LE,
        period_size=1024,
        periods=3
    )

    print("Capture configuration:")
    print(f"  Sample Rate: {config.sample_rate} Hz")
    print(f"  Channels: {config.channels}")
    print(f"  Bit Depth: {config.bit_depth}")
    print(f"  Period Size: {config.period_size} frames")
    print(f"  Latency: {config.latency_ms:.2f} ms")
    print(f"  Bytes per period: {config.period_bytes}")
    print()

    # Initialize capture
    capture = USBAudioCapture(config)

    if not capture.open():
        print("ERROR: Failed to open capture device")
        sys.exit(1)

    # Capture for 10 seconds and save to file
    duration = 10
    output_file = '/tmp/turntabler_test_capture.raw'

    print(f"Capturing audio for {duration} seconds...")
    print(f"Output file: {output_file}")
    print()
    print("Press Ctrl+C to stop early")
    print()

    # Track total bytes using mutable container for closure
    stats = {'total_bytes': 0}

    try:
        with open(output_file, 'wb') as f:
            def write_callback(data: bytes):
                f.write(data)
                stats['total_bytes'] += len(data)

            for chunk in capture.capture_stream(
                callback=write_callback,
                duration_seconds=duration
            ):
                # Progress indicator
                if capture.frames_captured % (config.sample_rate // 4) == 0:
                    elapsed = capture.frames_captured / config.sample_rate
                    print(f"  {elapsed:.1f}s captured...", end='\r')

    except KeyboardInterrupt:
        print("\nStopped by user")
    except CaptureError as e:
        print(f"\nCapture error: {e}")
        sys.exit(1)
    finally:
        capture.close()

    print()
    print("=" * 60)
    print("Capture Complete")
    print("=" * 60)
    print()
    print(f"Total bytes captured: {stats['total_bytes']:,}")
    print(f"Total frames captured: {capture.frames_captured:,}")
    print(f"Duration: {capture.frames_captured / config.sample_rate:.2f}s")
    print(f"Buffer overruns: {capture.overruns}")
    print()
    print(f"Audio saved to: {output_file}")
    print()
    print("To play with aplay:")
    print(f"  aplay -f S16_LE -r {config.sample_rate} -c {config.channels} {output_file}")
    print()
    print("To convert to WAV:")
    print(f"  sox -r {config.sample_rate} -e signed -b {config.bit_depth} -c {config.channels} \\")
    print(f"      {output_file} {output_file.replace('.raw', '.wav')}")
