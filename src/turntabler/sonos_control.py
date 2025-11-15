"""
SoCo control script - discovers Sonos devices and tells them to play our stream.
"""

from soco import discover
import socket
import time


def get_my_ip():
    """Get this machine's IP address on local network"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just for getting local IP
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
        print("   Check network connection and ensure Sonos is on same subnet")
        return

    # List all devices
    print(f"✅ Found {len(devices)} device(s):")
    for d in devices:
        print(f"   - {d.player_name} ({d.ip_address})")

    # Find Beam (or use first device)
    beam = next((d for d in devices if "Beam" in d.player_name), list(devices)[0])
    print(f"\n🎯 Target device: {beam.player_name}")

    # Handle grouping - CRITICAL for grouped devices
    print("\n🎛️  Checking group configuration...")
    if beam.group:
        members = [m.player_name for m in beam.group.members]
        coordinator = beam.group.coordinator
        print(f"   Device is grouped with: {', '.join(members)}")
        print(f"   Coordinator: {coordinator.player_name}")
        playback_device = coordinator
    else:
        print("   Device is standalone (not grouped)")
        playback_device = beam

    print(f"   Sending commands to: {playback_device.player_name}")

    # Build stream URL
    my_ip = get_my_ip()
    stream_url = f"http://{my_ip}:8000/turntable.flac"

    print(f"\n📻 Stream URL: {stream_url}")
    print(f"🎵 Starting playback...")

    try:
        # IMPORTANT: Use playback_device (coordinator if grouped) for all commands
        # NOTE: Testing WITHOUT force_radio for plain HTTP chunked streaming
        # - force_radio=True requires ICY metadata (SHOUTcast protocol)
        # - This test uses simple HTTP chunked encoding (no metadata)
        # - Tests if Sonos accepts infinite FLAC chunks via plain HTTP
        # - Mimics real turntable: continuous chunks, no special protocol
        playback_device.play_uri(
            stream_url,
            title="TurnTabler POC Test",
            # force_radio=False,  # Test plain HTTP chunked stream
        )

        print("✅ Stream started successfully!")
        print("🔍 Monitoring Sonos state transitions...")

        # Monitor state transitions closely in first 10 seconds
        # Query playback_device (which may be coordinator if grouped)
        for i in range(10):
            time.sleep(1)
            info = playback_device.get_current_transport_info()
            track_info = playback_device.get_current_track_info()
            state = info["current_transport_state"]
            title = track_info.get("title", "N/A")
            position = track_info.get("position", "N/A")

            print(
                f"  [{i + 1}s] State: {state:12} | Title: {title:20} | Pos: {position}"
            )

            if state == "PLAYING":
                print("\n✅ AUDIO PLAYING!")
                break
            elif state == "STOPPED":
                print("\n❌ Playback stopped. Stream may be incompatible.")
                break

        print("\n📊 FINAL STATUS")
        info = playback_device.get_current_transport_info()
        track_info = playback_device.get_current_track_info()
        print(f"  Playback state: {info['current_transport_state']}")
        print(f"  Current track: {track_info['title']}")

        print("\n✅ POC TEST RUNNING")
        print("   If audio is playing, test will run for 10+ minutes")
        print("   Press Ctrl+C to stop when done")

        # Keep script running so we can observe
        elapsed = 10
        while True:
            time.sleep(60)
            elapsed += 60
            status = playback_device.get_current_transport_info()["current_transport_state"]
            print(f"⏱️  Status after {elapsed}s: {status}")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping playback...")
        playback_device.stop()
        print("✅ Playback stopped")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure FastAPI server is running")
        print("   2. Check firewall allows port 8000")
        print(f"   3. Verify stream accessible: curl http://{my_ip}:8000/")


if __name__ == "__main__":
    main()
