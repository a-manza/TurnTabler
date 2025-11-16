"""
Complete end-to-end test of TurnTabler streaming.

This test validates the full production flow using the TurnTablerStreamer class.
The test uses the EXACT same code path as production - only the audio source
changes from synthetic to USB.
"""

import logging
import sys
from typing import Optional

# Import production streamer
from turntabler.streaming import TurnTablerStreamer

logger = logging.getLogger(__name__)


# For backwards compatibility, create alias to production streamer
StreamingTest = TurnTablerStreamer


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

    # Run test using production TurnTablerStreamer
    streamer = TurnTablerStreamer(
        sonos_ip=args.sonos_ip,
        audio_frequency=args.frequency,
        test_duration_seconds=args.duration,
        port=args.port
    )

    stats = streamer.run(audio_source=args.source, device=args.device)

    # Test passes if it ran and final state is PLAYING (or at least not SETUP_FAILED)
    success = stats.final_state != "SETUP_FAILED" and stats.final_state != "SERVER_FAILED"
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
