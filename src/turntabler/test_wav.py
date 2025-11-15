"""
Test with WAV file to isolate FLAC encoding issues.
WAV is uncompressed, simplest audio format - good control test.
"""

from soco import discover
import socket
import time


def get_my_ip():
    """Get local IP address on network"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    print("🔍 Discovering Sonos devices...")
    devices = discover(timeout=5)

    if not devices:
        print("❌ No Sonos devices found!")
        return

    device = list(devices)[0]
    print(f"\n🎯 Target device: {device.player_name} ({device.ip_address})")

    # Handle grouping - CRITICAL for grouped devices
    print("\n🎛️  Checking group configuration...")
    if device.group:
        members = [m.player_name for m in device.group.members]
        coordinator = device.group.coordinator
        print(f"   Device is grouped with: {', '.join(members)}")
        print(f"   Coordinator: {coordinator.player_name}")
        playback_device = coordinator
    else:
        print("   Device is standalone (not grouped)")
        playback_device = device

    print(f"   Sending commands to: {playback_device.player_name}")

    # Check and adjust volume
    print(f"\n📊 Device Status:")
    print(f"  Volume: {playback_device.volume}%")
    print(f"  Muted: {playback_device.mute}")

    if playback_device.volume == 0:
        print("\n⚠️  Setting volume to 50% (was 0%)")
        playback_device.volume = 50

    if playback_device.mute:
        print("\n⚠️  Unmuting device (was muted)")
        playback_device.mute = False

    my_ip = get_my_ip()
    stream_url = f"http://{my_ip}:8000/turntable.wav"

    print(f"\n🎵 Testing WAV file (uncompressed control test)")
    print(f"📻 Stream URL: {stream_url}")

    try:
        # Testing WITHOUT force_radio=True
        # force_radio requires ICY metadata that plain HTTP file server doesn't provide
        playback_device.play_uri(
            stream_url,
            title="TurnTabler WAV Test",
            # force_radio=True,  # Removed - testing as regular file first
        )

        print("✅ WAV playback started")
        print("🔍 Monitoring state transitions...")

        for i in range(10):
            time.sleep(1)
            info = playback_device.get_current_transport_info()
            state = info["current_transport_state"]
            track = playback_device.get_current_track_info().get("title", "N/A")
            print(f"  [{i + 1}s] State: {state:12} | Title: {track}")

            if state == "PLAYING":
                print("\n✅ ✅ ✅ WAV AUDIO PLAYING!")
                print("   This means: Format compatibility is OK")
                print("   FLAC issue likely: Encoding parameters or codec mismatch")
                return

        print("\n❌ WAV didn't play either")
        print("   This suggests deeper issue (not FLAC-specific)")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        device.stop()
        print("\n🛑 Playback stopped")


if __name__ == "__main__":
    main()
