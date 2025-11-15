#!/bin/bash
# Regenerate test audio with proper parameters for Sonos FLAC compatibility

set -e

cd /home/a_manza/dev/turntabler

echo "🎵 Regenerating test audio files..."

# === FLAC with explicit Sonos-compatible parameters ===
echo ""
echo "1️⃣ Creating FLAC file (Sonos native format)..."
echo "   - Duration: 30 seconds"
echo "   - Sample rate: 48000 Hz (Sonos maximum)"
echo "   - Channels: 2 (stereo)"
echo "   - Bit depth: 16-bit (Sonos official spec)"
echo "   - Frequency: 440 Hz (musical A note)"

# Use sox to generate proper audio, then encode to FLAC
sox -n -r 48000 -c 2 -b 16 test-temp.wav synth 30 sine 440

# Encode to FLAC with explicit parameters
ffmpeg -y \
  -i test-temp.wav \
  -c:a flac \
  -sample_fmt s16 \
  test-loop.flac

rm test-temp.wav

# Verify FLAC
echo ""
echo "2️⃣ Verifying FLAC file specifications..."
ffprobe -v error -select_streams a:0 -show_entries stream=codec_type,sample_rate,channels,bits_per_sample -of csv=p=0 test-loop.flac

# === WAV as control test (simplest format) ===
echo ""
echo "3️⃣ Creating WAV file (control test - uncompressed)..."
echo "   - Same specs as FLAC but uncompressed"
echo "   - Simpler codec = easier to debug"

sox -n -r 48000 -c 2 -b 16 test-loop.wav synth 30 sine 440

echo ""
echo "✅ All test audio files regenerated:"
echo "   - test-loop.flac (FLAC, 48kHz, 16-bit, stereo)"
echo "   - test-loop.wav (WAV, 48kHz, 16-bit, stereo)"
echo ""
echo "📝 FLAC file details:"
ffprobe -v quiet -print_format default=noprint_wrappers=1 test-loop.flac 2>&1 | head -10
