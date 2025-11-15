#!/usr/bin/env python3
"""
Pre-generate FLAC chunks for continuous streaming test.

Creates 10 FLAC files with different frequencies (musical scale).
Each chunk is 3 seconds, 48kHz, 16-bit, stereo FLAC.
Use different frequencies so you can hear the chunks cycling.
"""

import subprocess
from pathlib import Path

CHUNKS_DIR = Path(__file__).parent / "src" / "turntabler" / "chunks"
CHUNK_DURATION = 3  # seconds
SAMPLE_RATE = 48000
CHANNELS = 2
BIT_DEPTH = 16

# Musical scale frequencies (A minor scale)
FREQUENCIES = [
    440,   # A4 - concert pitch
    493,   # B4
    523,   # C5
    587,   # D5
    659,   # E5
    698,   # F5
    783,   # G5
    880,   # A5 (one octave up)
    987,   # B5
    1046,  # C6
]


def generate_chunk(index: int, frequency: float):
    """Generate a single FLAC chunk with given frequency."""
    chunk_file = CHUNKS_DIR / f"chunk_{index:02d}.flac"

    print(f"📝 Generating chunk {index}: {frequency}Hz → {chunk_file.name}")

    # Generate WAV with sox
    wav_temp = CHUNKS_DIR / f"temp_{index}.wav"
    sox_cmd = [
        "sox",
        "-n",
        "-r", str(SAMPLE_RATE),
        "-c", str(CHANNELS),
        "-b", str(BIT_DEPTH),
        str(wav_temp),
        "synth",
        str(CHUNK_DURATION),
        "sine",
        str(frequency),
    ]

    try:
        subprocess.run(sox_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ sox failed: {e.stderr.decode()}")
        return False

    # Encode WAV to FLAC with ffmpeg
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(wav_temp),
        "-c:a", "flac",
        "-sample_fmt", "s16",
        str(chunk_file),
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg failed: {e.stderr.decode()}")
        return False

    # Clean up temp WAV
    wav_temp.unlink()

    # Verify file exists and has content
    if chunk_file.exists():
        size_kb = chunk_file.stat().st_size / 1024
        print(f"   ✅ Created {chunk_file.name} ({size_kb:.1f} KB)")
        return True
    else:
        print(f"   ❌ File not created: {chunk_file}")
        return False


def main():
    print("🎵 Pre-generating FLAC chunks for continuous streaming test\n")
    print(f"📁 Output directory: {CHUNKS_DIR}")
    print(f"📊 Specs: {CHUNK_DURATION}s, {SAMPLE_RATE}Hz, {BIT_DEPTH}-bit, {CHANNELS}-channel FLAC\n")

    # Ensure directory exists
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for index, frequency in enumerate(FREQUENCIES):
        if generate_chunk(index, frequency):
            success_count += 1

    print(f"\n✅ Generated {success_count}/{len(FREQUENCIES)} chunks successfully")

    if success_count > 0:
        print(f"\n📝 Chunk files ready for streaming:")
        for chunk_file in sorted(CHUNKS_DIR.glob("chunk_*.flac")):
            size_kb = chunk_file.stat().st_size / 1024
            print(f"   - {chunk_file.name} ({size_kb:.1f} KB)")

        print(f"\n🎵 When streaming:")
        print(f"   - Each chunk plays for {CHUNK_DURATION} seconds")
        print(f"   - Different frequencies cycle through (you'll hear pitch changes)")
        print(f"   - Total cycle: {len(FREQUENCIES) * CHUNK_DURATION}s = {len(FREQUENCIES) * CHUNK_DURATION / 60:.1f} minutes")
        print(f"\n✨ Ready to test with streaming_realtime.py!")
    else:
        print("\n❌ No chunks generated. Check that sox and ffmpeg are installed.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
