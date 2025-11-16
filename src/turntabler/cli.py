"""
TurnTabler CLI - Stream vinyl records to Sonos speakers.

Simple, modern CLI using Typer with production-first defaults.
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from turntabler.streaming import TurnTablerStreamer
from turntabler.usb_audio import USBAudioDeviceManager

# Create Typer app
app = typer.Typer(
    name="turntabler",
    help="Stream vinyl records to Sonos speakers with lossless audio quality",
    add_completion=True,
    no_args_is_help=True,
)

# Test subcommands
test_app = typer.Typer(
    help="Test and validate streaming setup",
    no_args_is_help=True,
)
app.add_typer(test_app, name="test")


def setup_logging(verbose: bool = False, quiet: bool = False):
    """Configure logging based on CLI flags."""
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@app.command()
def stream(
    # Audio source selection (mutually exclusive via logic)
    synthetic: Annotated[
        bool, typer.Option("--synthetic", help="Generate test tone (440Hz sine wave)")
    ] = False,
    file: Annotated[
        Optional[Path], typer.Option("--file", help="Stream from WAV file")
    ] = None,
    # Source-specific options
    device: Annotated[
        Optional[str],
        typer.Option("--device", help="USB ALSA device (auto-detect if omitted)"),
    ] = None,
    frequency: Annotated[
        float, typer.Option("--frequency", help="Tone frequency for synthetic (Hz)")
    ] = 440.0,
    # Sonos configuration
    sonos_ip: Annotated[
        Optional[str],
        typer.Option("--sonos-ip", help="Sonos speaker IP (auto-discover if omitted)"),
    ] = None,
    stream_name: Annotated[
        str, typer.Option("--stream-name", help="Display name in Sonos app")
    ] = "TurnTabler",
    # Server configuration
    host: Annotated[
        str, typer.Option("--host", help="Server bind address")
    ] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", help="Server port")] = 5901,
    # Logging
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable debug logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Minimal output")
    ] = False,
):
    """
    Stream audio to Sonos speakers.

    Defaults to USB audio input with auto-discovery of both USB device and Sonos speaker.
    This is the main production command - just plug in your turntable and run.

    Examples:

        # Production: Stream from USB to auto-discovered Sonos
        turntabler stream

        # Specify Sonos speaker
        turntabler stream --sonos-ip 192.168.1.100

        # Specify USB device
        turntabler stream --device hw:CARD=UCA222,DEV=0

        # Test with synthetic audio
        turntabler stream --synthetic

        # Stream from file
        turntabler stream --file test.wav
    """
    setup_logging(verbose, quiet)

    # Validate mutually exclusive options
    if synthetic and file:
        typer.secho(
            "Error: Cannot use both --synthetic and --file",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    # Determine audio source type
    if synthetic:
        source_type = "synthetic"
        typer.echo(f"🎵 Audio source: Synthetic ({frequency}Hz sine wave)")
    elif file:
        if not file.exists():
            typer.secho(f"Error: File not found: {file}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        source_type = f"file:{file}"
        typer.echo(f"🎵 Audio source: File ({file.name})")
    else:
        # Default: USB
        source_type = "usb"
        typer.echo("🎵 Audio source: USB audio interface")

        # If no device specified, check if USB device exists
        if not device:
            try:
                manager = USBAudioDeviceManager()
                detected = manager.detect_usb_audio_device()
                if not detected:
                    typer.secho(
                        "⚠️  Warning: No USB audio device detected",
                        fg=typer.colors.YELLOW,
                    )
                    typer.echo("\nTroubleshooting:")
                    typer.echo("  • List devices: turntabler list")
                    typer.echo("  • Test with synthetic: turntabler stream --synthetic")
                    typer.echo(
                        "\nContinuing anyway (will fail if USB unavailable)...\n"
                    )
            except Exception as e:
                if not quiet:
                    typer.secho(
                        f"⚠️  Warning: Could not detect USB device: {e}",
                        fg=typer.colors.YELLOW,
                    )

    # Display configuration
    typer.echo(f"🌐 Server: {host}:{port}")
    typer.echo(f"🔊 Sonos: {'auto-discover' if not sonos_ip else sonos_ip}")
    typer.echo(f"📻 Stream name: {stream_name}")
    typer.echo()

    # Create and run streamer
    try:
        streamer = TurnTablerStreamer(
            sonos_ip=sonos_ip,
            audio_frequency=frequency,
            test_duration_seconds=None,  # Run indefinitely
            host=host,
            port=port,
            stream_name=stream_name,
        )

        stats = streamer.run(audio_source=source_type, device=device)

        # Display results
        if stats.errors:
            typer.echo()
            typer.secho("⚠️  Completed with warnings:", fg=typer.colors.YELLOW)
            for error in stats.errors:
                typer.echo(f"  • {error}")

        typer.echo()
        typer.secho(
            f"✓ Streaming completed: {int(stats.duration_seconds)}s",
            fg=typer.colors.GREEN,
        )

    except KeyboardInterrupt:
        typer.echo("\n")
        typer.secho("✓ Stopped by user", fg=typer.colors.GREEN)
        raise typer.Exit(0)
    except Exception as e:
        typer.echo()
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        typer.echo("\nFor help: turntabler --help", err=True)
        raise typer.Exit(2)


@test_app.command("quick")
def test_quick(
    sonos_ip: Annotated[
        Optional[str],
        typer.Option("--sonos-ip", help="Sonos speaker IP (auto-discover if omitted)"),
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Server port")] = 5901,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable debug logging")
    ] = False,
):
    """
    Quick connectivity test (~30 seconds).

    Validates that:
      • HTTP server starts correctly
      • Sonos speaker is reachable
      • Playback initiates successfully

    Uses synthetic audio for fast, reliable testing.
    """
    setup_logging(verbose, False)

    typer.echo("🧪 Running quick connectivity test...\n")

    try:
        streamer = TurnTablerStreamer(
            sonos_ip=sonos_ip,
            audio_frequency=440.0,
            test_duration_seconds=30,
            port=port,
            stream_name="TurnTabler Quick Test",
        )

        stats = streamer.run(audio_source="synthetic")

        typer.echo()
        if stats.final_state == "PLAYING" and not stats.errors:
            typer.secho("✓ Test passed!", fg=typer.colors.GREEN)
            typer.echo(f"  • Duration: {int(stats.duration_seconds)}s")
            typer.echo("  • HTTP server: OK")
            typer.echo("  • Sonos connection: OK")
            typer.echo("  • Playback: OK")
        else:
            typer.secho("⚠️  Test completed with issues:", fg=typer.colors.YELLOW)
            typer.echo(f"  • Duration: {int(stats.duration_seconds)}s")
            typer.echo(f"  • Final state: {stats.final_state}")
            if stats.errors:
                for error in stats.errors:
                    typer.echo(f"  • {error}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        typer.echo("\n")
        typer.secho("✗ Test interrupted", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo()
        typer.secho(f"✗ Test failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@test_app.command("full")
def test_full(
    sonos_ip: Annotated[
        Optional[str],
        typer.Option("--sonos-ip", help="Sonos speaker IP (auto-discover if omitted)"),
    ] = None,
    duration: Annotated[
        int, typer.Option("--duration", help="Test duration in seconds")
    ] = 600,
    source: Annotated[
        str,
        typer.Option(
            "--source", help="Audio source: 'synthetic', 'file:<path>', or 'usb'"
        ),
    ] = "synthetic",
    device: Annotated[
        Optional[str], typer.Option("--device", help="USB ALSA device (for USB source)")
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Server port")] = 5901,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable debug logging")
    ] = False,
):
    """
    Full end-to-end test with statistics.

    Runs complete streaming validation for extended duration (default: 10 minutes).
    Useful for:
      • Validating stability
      • Performance benchmarking
      • Hardware testing

    Examples:

        # Default: 10-minute synthetic test
        turntabler test full

        # 5-minute USB test
        turntabler test full --duration 300 --source usb

        # File-based test
        turntabler test full --source file:test.wav --duration 60
    """
    setup_logging(verbose, False)

    typer.echo(f"🧪 Running full end-to-end test ({duration}s)...\n")

    try:
        streamer = TurnTablerStreamer(
            sonos_ip=sonos_ip,
            test_duration_seconds=duration,
            port=port,
            stream_name="TurnTabler Full Test",
        )

        stats = streamer.run(audio_source=source, device=device)

        typer.echo()
        if stats.final_state == "PLAYING" and not stats.errors:
            typer.secho("✓ Test completed successfully!", fg=typer.colors.GREEN)
        else:
            typer.secho("⚠️  Test completed with issues:", fg=typer.colors.YELLOW)

        typer.echo(f"  • Duration: {int(stats.duration_seconds)}s")
        typer.echo(f"  • Final state: {stats.final_state}")

        if stats.errors:
            typer.echo("  • Errors:")
            for error in stats.errors:
                typer.echo(f"    - {error}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        typer.echo("\n")
        typer.secho("✓ Test stopped by user", fg=typer.colors.GREEN)
        raise typer.Exit(0)
    except Exception as e:
        typer.echo()
        typer.secho(f"✗ Test failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("list")
def list_devices():
    """
    List available USB audio devices.

    Displays all USB audio interfaces detected by ALSA.
    Useful for identifying the correct device name for --device option.

    Example output:
        Available USB audio devices:

          • hw:CARD=UCA222,DEV=0

        Use with: turntabler stream --device hw:CARD=UCA222,DEV=0
    """
    try:
        manager = USBAudioDeviceManager()
        devices = manager.list_capture_devices()

        if not devices:
            typer.echo("No USB audio devices found")
            typer.echo("\nTroubleshooting:")
            typer.echo("  • Ensure USB audio interface is connected")
            typer.echo("  • Check ALSA: arecord -l")
            typer.echo("  • Verify permissions (may need to be in 'audio' group)")
            raise typer.Exit(1)

        typer.echo("Available USB audio devices:\n")
        for device in devices:
            typer.echo(f"  • {device.device_name} ({device.card_name})")

        typer.echo("\nUse with: turntabler stream --device <name>")

    except ImportError as e:
        typer.secho(
            f"Error: pyalsaaudio not available: {e}", fg=typer.colors.RED, err=True
        )
        typer.echo("Install with: uv add pyalsaaudio", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
