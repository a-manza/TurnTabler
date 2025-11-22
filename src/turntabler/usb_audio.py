"""
USB Audio device detection and management for TurnTabler.

This module handles ALSA device enumeration and configuration for USB audio
interfaces. It provides robust device detection with filtering of internal
sound cards and support for device identification by name pattern.

Typical usage:
    >>> from turntabler.usb_audio import detect_usb_audio_device, USBAudioDeviceManager
    >>>
    >>> # Simple detection
    >>> device = detect_usb_audio_device()
    >>> print(device)  # 'hw:CARD=UCA222,DEV=0'
    >>>
    >>> # Advanced usage
    >>> manager = USBAudioDeviceManager()
    >>> devices = manager.list_capture_devices()
    >>> for dev in devices:
    ...     print(f"{dev.card_name}: {dev.device_name}")
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import alsaaudio

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """
    Represents an ALSA audio capture device.

    Attributes:
        device_name: ALSA device string (e.g., 'hw:CARD=UCA222,DEV=0')
        card_number: Card number (e.g., 1), or -1 if unknown
        card_name: Human-readable card name (e.g., 'UCA222')
        device_number: Device number (typically 0)
    """

    device_name: str
    card_number: int
    card_name: str
    device_number: int = 0

    def __str__(self) -> str:
        return f"{self.card_name} ({self.device_name})"


class USBAudioDeviceManager:
    """
    Manages USB audio device detection and enumeration.

    This class provides methods to list, find, and query ALSA audio capture
    devices. It automatically filters out internal sound cards to focus on
    USB audio interfaces.
    """

    # Preferred device patterns (checked first, in order)
    PREFERRED_DEVICE_PATTERNS = ["CODEC", "UCA"]

    # Patterns for internal sound cards to filter out
    INTERNAL_CARD_PATTERNS = ["PCH", "Intel", "Analog", "Built-in", "HDA"]

    @staticmethod
    def list_capture_devices() -> List[AudioDevice]:
        """
        List all available ALSA capture devices.

        Returns:
            List of AudioDevice objects representing available capture devices.
            Empty list if no devices found.

        Example:
            >>> manager = USBAudioDeviceManager()
            >>> devices = manager.list_capture_devices()
            >>> for dev in devices:
            ...     print(dev.card_name)
        """
        devices = []

        try:
            alsa_devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
        except alsaaudio.ALSAAudioError as e:
            logger.error(f"Failed to enumerate ALSA devices: {e}")
            return devices

        # Regex to parse hw:CARD=CardName,DEV=N format
        hw_pattern = re.compile(r"hw:CARD=([^,]+),DEV=(\d+)")

        for dev_str in alsa_devices:
            match = hw_pattern.match(dev_str)
            if match:
                card_name = match.group(1)
                dev_num = int(match.group(2))

                # Extract card number if possible
                card_num = USBAudioDeviceManager._get_card_number(dev_str)

                devices.append(
                    AudioDevice(
                        device_name=dev_str,
                        card_number=card_num,
                        card_name=card_name,
                        device_number=dev_num,
                    )
                )

        logger.debug(f"Found {len(devices)} ALSA capture device(s)")
        return devices

    @staticmethod
    def _get_card_number(device_str: str) -> int:
        """
        Extract card number from device string.

        Attempts to parse card number from various ALSA device string formats.
        Falls back to -1 if card number cannot be determined.

        Args:
            device_str: ALSA device string (e.g., 'hw:1,0' or 'hw:CARD=UCA222,DEV=0')

        Returns:
            Card number (0, 1, 2, ...) or -1 if unknown
        """
        # Try to match hw:X,Y format first
        simple_pattern = re.compile(r"hw:(\d+),(\d+)")
        match = simple_pattern.match(device_str)
        if match:
            return int(match.group(1))

        # Could extend this to parse /proc/asound/cards if needed
        # For now, return -1 for named devices
        return -1

    @staticmethod
    def find_device(pattern: Optional[str] = None) -> Optional[AudioDevice]:
        """
        Find USB audio capture device by name pattern.

        This method filters out internal sound cards and searches for USB
        audio interfaces. If a pattern is provided, it searches for devices
        matching that pattern. Otherwise, it returns the first USB device found.

        Args:
            pattern: Regex pattern to match card name (e.g., 'UCA222', 'Scarlett').
                    Case-insensitive. If None, returns first non-internal device.

        Returns:
            AudioDevice object if found, None otherwise

        Example:
            >>> manager = USBAudioDeviceManager()
            >>> device = manager.find_device('Scarlett')
            >>> if device:
            ...     print(f"Found: {device.device_name}")
        """
        devices = USBAudioDeviceManager.list_capture_devices()

        # If no explicit pattern, check for preferred devices first
        if not pattern:
            for pref_pattern in USBAudioDeviceManager.PREFERRED_DEVICE_PATTERNS:
                for dev in devices:
                    if pref_pattern.lower() in dev.card_name.lower():
                        logger.info(f"Found preferred device: {dev}")
                        return dev

        # Filter out internal sound cards
        usb_devices = [
            dev
            for dev in devices
            if not any(
                p.lower() in dev.card_name.lower()
                for p in USBAudioDeviceManager.INTERNAL_CARD_PATTERNS
            )
        ]

        logger.debug(f"Found {len(usb_devices)} USB audio device(s) after filtering")

        if pattern:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                return None

            for device in usb_devices:
                if regex.search(device.card_name):
                    logger.info(f"Found matching device: {device}")
                    return device

            logger.warning(f"No device found matching pattern: {pattern}")
            return None

        elif usb_devices:
            # Return first USB device
            device = usb_devices[0]
            logger.info(f"Auto-detected USB device: {device}")
            return device

        logger.warning("No USB audio devices found")
        return None

    @staticmethod
    def get_device_info(device_name: str) -> dict:
        """
        Get information about a specific device.

        Attempts to open the device to verify accessibility. Returns a
        dictionary with device status and any error information.

        Args:
            device_name: ALSA device string (e.g., 'hw:1,0')

        Returns:
            Dictionary with keys:
                - 'device': Device name
                - 'accessible': True if device can be opened
                - 'error': Error message (if not accessible)

        Example:
            >>> manager = USBAudioDeviceManager()
            >>> info = manager.get_device_info('hw:CARD=UCA222,DEV=0')
            >>> if info['accessible']:
            ...     print("Device is ready")
        """
        try:
            # Open device temporarily to verify accessibility
            pcm = alsaaudio.PCM(
                alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device=device_name
            )
            pcm.close()

            return {
                "device": device_name,
                "accessible": True,
            }

        except alsaaudio.ALSAAudioError as e:
            return {"device": device_name, "accessible": False, "error": str(e)}


def detect_usb_audio_device(preferred_device: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to detect USB audio device.

    This is a simple wrapper around USBAudioDeviceManager.find_device() that
    returns just the ALSA device string (not the full AudioDevice object).

    Args:
        preferred_device: Regex pattern for preferred device name (e.g., 'UCA222')

    Returns:
        ALSA device string (e.g., 'hw:CARD=UCA222,DEV=0') or None if not found

    Example:
        >>> device = detect_usb_audio_device('Scarlett')
        >>> if device:
        ...     print(f"Using: {device}")
    """
    manager = USBAudioDeviceManager()
    device = manager.find_device(preferred_device)
    return device.device_name if device else None


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("USB Audio Device Detection")
    print("=" * 60)
    print()

    # List all capture devices
    manager = USBAudioDeviceManager()
    devices = manager.list_capture_devices()

    print(f"Found {len(devices)} capture device(s):")
    print()

    for dev in devices:
        print(f"  Card: {dev.card_name} (#{dev.card_number})")
        print(f"  Device: {dev.device_name}")
        print(f"  Device Number: {dev.device_number}")

        # Get device info
        info = manager.get_device_info(dev.device_name)
        print(f"  Accessible: {info['accessible']}")
        if not info["accessible"]:
            print(f"  Error: {info.get('error', 'Unknown')}")
        print()

    # Try to find USB audio device
    print("=" * 60)
    print("Auto-detecting USB Audio Device")
    print("=" * 60)
    print()

    usb_device = manager.find_device()
    if usb_device:
        print(f"Detected USB audio device: {usb_device.card_name}")
        print(f"ALSA device string: {usb_device.device_name}")
        print()

        # Test accessibility
        info = manager.get_device_info(usb_device.device_name)
        if info["accessible"]:
            print("Device is accessible and ready to use")
        else:
            print(f"Device found but not accessible: {info.get('error')}")
    else:
        print("No USB audio device found")
        print()
        print("Make sure:")
        print("  1. USB audio interface is connected")
        print("  2. Device is powered on (if external power required)")
        print("  3. User has permissions (add to 'audio' group)")
