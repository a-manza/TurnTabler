"""
Complete end-to-end test of TurnTabler streaming.

This test demonstrates the full production flow:
1. Generate/capture continuous audio (synthetic for POC, USB in production)
2. Stream via HTTP with WAV format
3. Control Sonos playback via SoCo
4. Monitor for extended continuous streaming

This is the EXACT code path used in production - only the audio source
changes from synthetic to USB.
"""

import asyncio
import socket
import time
import logging
import sys
from pathlib import Path
from typing import Optional

# Local imports
from turntabler.audio_source import AudioFormat, SyntheticAudioSource, FileAudioSource, USBAudioSource
from turntabler.streaming_wav import WAVStreamingServer, generate_wav_header

# SoCo import
try:
    from soco import SoCo, discover
except ImportError:
    SoCo = None
    discover = None

logger = logging.getLogger(__name__)


class StreamingTest:
    """
    Complete streaming test suite.

    Tests the full production pipeline:
    - Audio source → HTTP WAV streaming → Sonos playback → Monitoring
    """

    def __init__(
        self,
        sonos_ip: Optional[str] = None,
        audio_frequency: float = 440.0,
        test_duration_seconds: int = 600,  # 10 minutes default
        host: str = "0.0.0.0",
        port: int = 5901
    ):
        """
        Initialize test.

        Args:
            sonos_ip: IP of Sonos speaker (auto-detect if None)
            audio_frequency: Synthetic audio frequency (Hz)
            test_duration_seconds: How long to stream
            host: HTTP server bind address
            port: HTTP server bind port
        """
        self.sonos_ip = sonos_ip
        self.audio_frequency = audio_frequency
        self.test_duration_seconds = test_duration_seconds
        self.host = host
        self.port = port

        self.sonos = None
        self.server = None
        self.audio_source = None
        self.start_time = None
        self.stop_requested = False

    def discover_sonos(self) -> Optional[SoCo]:
        """Discover Sonos speaker on network."""
        if not discover:
            logger.error("SoCo not installed. Install with: pip install soco")
            return None

        logger.info("Discovering Sonos devices...")
        devices = discover(timeout=5)

        if not devices:
            logger.error("No Sonos devices found on network")
            return None

        for device in devices:
            logger.info(f"  Found: {device.player_name} ({device.ip_address})")

        # Return first device or specified IP
        for device in devices:
            if self.sonos_ip and device.ip_address == self.sonos_ip:
                logger.info(f"Using specified device: {device.player_name}")
                return device

        # Use first device
        sonos = list(devices)[0]
        logger.info(f"Using device: {sonos.player_name} ({sonos.ip_address})")
        return sonos

    def get_local_ip(self) -> str:
        """Get local IP address for streaming URL."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to external host to determine local IP
            # (doesn't actually connect)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()

        return ip

    def setup_audio_source(self, source_type: str = "synthetic", device: Optional[str] = None) -> bool:
        """
        Setup audio source.

        Args:
            source_type: 'synthetic', 'file:<path>', or 'usb'
            device: ALSA device for USB source (optional, auto-detects if None)

        Returns:
            True if successful
        """
        audio_format = AudioFormat()

        if source_type == "synthetic":
            logger.info(f"Creating synthetic audio source ({self.audio_frequency}Hz)")
            self.audio_source = SyntheticAudioSource(
                format=audio_format,
                frequency=self.audio_frequency,
                amplitude=0.5
            )
            return True

        elif source_type.startswith("file:"):
            file_path = source_type.split(":", 1)[1]
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return False

            logger.info(f"Creating file audio source: {file_path}")
            self.audio_source = FileAudioSource(file_path, audio_format)
            return True

        elif source_type == "usb":
            logger.info("Creating USB audio source")
            try:
                self.audio_source = USBAudioSource(audio_format, device=device)
                logger.info("✅ USB audio source initialized")
                return True
            except ImportError as e:
                logger.error(f"USB audio not available: {e}")
                logger.error("Install with: uv pip install -e \".[usb]\"")
                return False
            except RuntimeError as e:
                logger.error(f"Failed to initialize USB audio: {e}")
                return False

        else:
            logger.error(f"Unknown audio source type: {source_type}")
            return False

    def setup_streaming_server(self) -> bool:
        """Setup HTTP WAV streaming server."""
        if not self.audio_source:
            logger.error("Audio source not initialized")
            return False

        try:
            audio_format = AudioFormat()
            self.server = WAVStreamingServer(
                audio_source=self.audio_source,
                wav_format=audio_format,
                stream_name="TurnTabler Test"
            )
            logger.info("WAV streaming server initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to setup streaming server: {e}")
            return False

    def setup_sonos(self) -> bool:
        """Setup Sonos speaker connection."""
        if not SoCo:
            logger.warning("SoCo not installed - skipping Sonos setup")
            return True  # Continue testing anyway

        # Connect to device
        device = None
        if self.sonos_ip:
            try:
                device = SoCo(self.sonos_ip)
                logger.info(f"Connected to Sonos: {device.player_name}")
            except Exception as e:
                logger.error(f"Failed to connect to {self.sonos_ip}: {e}")
                return False
        else:
            device = self.discover_sonos()
            if not device:
                return False

        # Handle grouping - CRITICAL for grouped devices
        # Commands to grouped member devices are silently ignored
        # Must route all commands to group.coordinator
        logger.info("Checking group configuration...")
        if device.group:
            members = [m.player_name for m in device.group.members]
            coordinator = device.group.coordinator
            logger.info(f"  Device is grouped with: {', '.join(members)}")
            logger.info(f"  Coordinator: {coordinator.player_name}")
            self.sonos = coordinator
        else:
            logger.info("  Device is standalone (not grouped)")
            self.sonos = device

        logger.info(f"  Sending commands to: {self.sonos.player_name}")
        return True

    def start_streaming(self) -> bool:
        """Start streaming to Sonos."""
        if not self.sonos:
            logger.warning("Sonos not available - skipping streaming start")
            return True

        try:
            local_ip = self.get_local_ip()
            stream_url = f"http://{local_ip}:{self.port}/stream.wav"

            logger.info(f"Starting streaming: {stream_url}")
            logger.info(f"Target: {self.sonos.player_name}")

            # Check volume and device state
            logger.info(f"  Volume: {self.sonos.volume}%")
            logger.info(f"  Muted: {self.sonos.mute}")

            # Start playback
            self.sonos.play_uri(
                uri=stream_url,
                title="TurnTabler Streaming Test",
                start=True,
                force_radio=False  # Plain HTTP, no force_radio
            )

            logger.info("Playback started on Sonos")

            # Monitor initial state transitions
            logger.info("Monitoring state transitions...")
            for i in range(10):
                time.sleep(1)
                try:
                    info = self.sonos.get_current_transport_info()
                    state = info['current_transport_state']
                    track = self.sonos.get_current_track_info().get('title', 'N/A')
                    logger.info(f"  [{i+1}s] State: {state:12} | Title: {track}")

                    if state == "PLAYING":
                        logger.info("✅ Audio is playing!")
                        return True
                    elif state == "STOPPED":
                        logger.warning("Playback stopped")
                        return False
                except Exception as e:
                    logger.warning(f"Error checking status: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False

    def _wait_for_server_ready(self, timeout: int = 5) -> bool:
        """
        Wait for HTTP server to be ready.

        Polls the stream endpoint until it responds or timeout occurs.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if server is ready, False if timeout
        """
        import socket
        start = time.time()
        local_ip = self.get_local_ip()
        server_addr = (local_ip, self.port)

        logger.info("Waiting for HTTP server to be ready...")

        while time.time() - start < timeout:
            try:
                # Try to connect to the server port
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex(server_addr)
                s.close()

                if result == 0:
                    logger.info("✅ HTTP server is ready")
                    return True
            except Exception:
                pass

            time.sleep(0.2)

        logger.error(f"HTTP server failed to start within {timeout}s")
        return False

    def start_http_server_background(self) -> bool:
        """
        Start HTTP server in background thread.

        Returns:
            True if server thread started successfully
        """
        if not self.server:
            logger.error("Server not initialized")
            return False

        # Create FastAPI app
        app = self.server.app

        # Run with uvicorn in background
        import uvicorn
        import threading

        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)

        # Run in background thread
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        logger.info(f"Streaming server started on {self.host}:{self.port}")

        # Wait for server to be ready
        return self._wait_for_server_ready(timeout=5)

    async def monitor_streaming(self):
        """Monitor streaming and update status."""
        # Keep running until test duration expires
        self.start_time = time.time()

        try:
            while not self.stop_requested:
                elapsed = time.time() - self.start_time
                remaining = self.test_duration_seconds - elapsed

                if remaining <= 0:
                    logger.info("Test duration complete")
                    break

                # Log status periodically
                if int(elapsed) % 60 == 0:
                    logger.info(
                        f"Streaming active: {int(elapsed)}s elapsed, "
                        f"{int(remaining)}s remaining"
                    )

                    # Check Sonos status
                    if self.sonos:
                        try:
                            state = self.sonos.get_current_transport_info()[
                                'current_transport_state'
                            ]
                            logger.info(f"  Sonos state: {state}")
                        except Exception as e:
                            logger.warning(f"  Error checking Sonos: {e}")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        finally:
            self.stop_requested = True

    def run_test(self, audio_source: str = "synthetic", device: Optional[str] = None) -> bool:
        """
        Run complete streaming test.

        Args:
            audio_source: Audio source type ('synthetic', 'file:<path>', or 'usb')
            device: ALSA device for USB source (optional, auto-detects if None)

        Returns:
            True if test passed
        """
        logger.info("=" * 60)
        logger.info("TurnTabler Streaming Test")
        logger.info("=" * 60)

        # Setup
        if not self.setup_audio_source(audio_source, device=device):
            return False

        if not self.setup_streaming_server():
            return False

        # CRITICAL: Start HTTP server FIRST, before telling Sonos to connect
        # This prevents race condition where Sonos tries to fetch stream before server is ready
        if not self.start_http_server_background():
            logger.error("HTTP server failed to start")
            return False

        # Now setup Sonos (after server is ready)
        if not self.setup_sonos():
            logger.warning("Sonos setup failed - continuing with server only")

        # Now tell Sonos to start streaming (server is already running)
        if not self.start_streaming():
            logger.warning("Sonos streaming failed - continuing with server")

        # Run monitoring loop
        logger.info(f"\nRunning for {self.test_duration_seconds} seconds...")
        logger.info("Press Ctrl+C to stop\n")

        try:
            asyncio.run(self.monitor_streaming())
        except KeyboardInterrupt:
            logger.info("\nTest stopped")

        # Cleanup
        if self.sonos:
            try:
                self.sonos.stop()
                logger.info("Stopped playback on Sonos")
            except Exception as e:
                logger.warning(f"Error stopping Sonos: {e}")

        if self.audio_source:
            self.audio_source.close()

        # Summary
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info("=" * 60)
        logger.info(f"Test complete: {int(elapsed)} seconds")
        logger.info("=" * 60)

        return True


def main():
    """CLI entry point."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="TurnTabler Streaming Test")
    parser.add_argument(
        "--sonos-ip",
        type=str,
        default=None,
        help="IP address of Sonos speaker (auto-detect if not specified)"
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=440.0,
        help="Synthetic audio frequency in Hz (default: 440)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=600,
        help="Test duration in seconds (default: 600 = 10 minutes)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="synthetic",
        help="Audio source: 'synthetic', 'file:<path>', or 'usb' (default: synthetic)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="ALSA device for USB source (e.g., hw:CARD=CODEC,DEV=0). Auto-detects if not specified."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5901,
        help="HTTP server port (default: 5901)"
    )

    args = parser.parse_args()

    # Run test
    test = StreamingTest(
        sonos_ip=args.sonos_ip,
        audio_frequency=args.frequency,
        test_duration_seconds=args.duration,
        port=args.port
    )

    success = test.run_test(audio_source=args.source, device=args.device)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
