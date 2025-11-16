"""
Test SoCo with a known-working public radio URI.
If this plays audio, it proves SoCo/Sonos infrastructure works.
If this fails, the problem is device configuration, not our code.
"""

import time

from soco import discover


def main():
    print("🔍 Discovering Sonos devices...")
    devices = discover(timeout=5)

    if not devices:
        print("❌ No Sonos devices found!")
        return

    print(f"✅ Found {len(devices)} device(s)")

    # Get first device
    device = list(devices)[0]
    print(f"\n🎯 Target device: {device.player_name}")

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

    # Check volume and mute state before testing
    print("\n📊 Device Status Before Test:")
    print(f"  Volume: {playback_device.volume}%")
    print(f"  Muted: {playback_device.mute}")

    if playback_device.volume == 0:
        print("\n⚠️  WARNING: Volume is at 0%. Increasing to 50% for test.")
        playback_device.volume = 50

    if playback_device.mute:
        print("\n⚠️  WARNING: Device is muted. Unmuting.")
        playback_device.mute = False

    # Test with BBC Radio 4 (reliable, public, no auth needed)
    print("\n🎙️ Testing with known public radio stream...")
    print("   Using: BBC Radio 4 (UK public radio)")

    test_uri = "http://a.files.bbci.co.uk/media/live/manifesto/audio/m4a/live_radio4_lw_online_nonuk.m4a"

    try:
        playback_device.play_uri(test_uri, title="BBC Radio 4 Test")
        print("✅ play_uri() call succeeded")

        # Monitor state transitions
        print("\n🔍 Monitoring playback state...")
        for i in range(10):
            time.sleep(1)
            info = playback_device.get_current_transport_info()
            state = info["current_transport_state"]
            track = playback_device.get_current_track_info().get("title", "N/A")
            print(f"  [{i + 1}s] State: {state:12} | Title: {track}")

            if state == "PLAYING":
                print("\n✅ ✅ ✅ AUDIO PLAYING FROM PUBLIC RADIO!")
                print("   This means: SoCo, Sonos, network all work correctly.")
                print("   Problem is specific to our FLAC file or server.")
                return

        # If we get here, public URI didn't work either
        print("\n❌ Public radio didn't play either")
        print("   This suggests: Sonos configuration issue, not our code")
        print("   Try: Restart Sonos device, check network, verify Sonos app works")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Troubleshooting:")
        print("   1. Check Sonos is on same network")
        print("   2. Check firewall allows SoCo control (port 1400)")
        print("   3. Verify Sonos works via official app")


if __name__ == "__main__":
    main()
