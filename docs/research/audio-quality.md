# Audio Quality Requirements & Considerations

## Lossless Audio Explained

### What is Lossless?
**Lossless compression** preserves 100% of the original audio data. When decompressed, the output is bit-identical to the input.

**Common lossless formats:**
- ALAC (Apple Lossless) - used by AirPlay
- FLAC (Free Lossless Audio Codec) - most common on Linux
- WAV (uncompressed) - no compression, largest files
- AIFF (uncompressed) - Apple's WAV equivalent

### Lossy vs Lossless

| Aspect | Lossy (MP3, AAC) | Lossless (ALAC, FLAC) |
|--------|------------------|------------------------|
| File size | Small (~10% of WAV) | Medium (~50% of WAV) |
| Quality | Audible artifacts | Perfect reproduction |
| Use case | Streaming, portability | Archival, hi-fi playback |
| Vinyl streaming | **NOT ACCEPTABLE** | **Required** |

**Why lossless for vinyl:**
- Vinyl has warmth, character, and subtle details
- Lossy compression destroys the nuances that make vinyl special
- If you're going to the effort of streaming vinyl, preserve the quality!

## Audio Quality Specifications

### Bit Depth
**What it represents:** Dynamic range (difference between quietest and loudest sound)

- **16-bit:** 96 dB dynamic range (CD quality)
- **24-bit:** 144 dB dynamic range (exceeds human hearing)

**Vinyl consideration:** Most vinyl has ~60-70 dB dynamic range, but 24-bit capture prevents any quantization noise during processing.

**TurnTabler target:** 24-bit (maximum quality)

### Sample Rate
**What it represents:** How many times per second audio is measured

- **44.1 kHz:** CD standard, captures up to 22.05 kHz (above human hearing ~20 kHz)
- **48 kHz:** Video/pro audio standard, captures up to 24 kHz
- **96 kHz:** Hi-res audio, captures up to 48 kHz (ultrasonic)
- **192 kHz:** Extreme hi-res, captures up to 96 kHz

**Vinyl consideration:** Vinyl's frequency response typically maxes out around 20-25 kHz. 48 kHz is more than sufficient.

**TurnTabler target:** 48 kHz (maximum AirPlay 2 supports, sufficient for vinyl)

### AirPlay 2 Limitations

**Maximum supported:** 24-bit / 48 kHz stereo

**What this means:**
- If you capture at 24/96 or 24/192, AirPlay will downsample to 24/48
- Still excellent quality, exceeds CD (16/44.1)
- Transparent for vinyl playback

## USB Audio Interface Quality

### Entry Level: Behringer UCA202 ($30-40)
- **Specs:** 16-bit / 48 kHz
- **ADC:** Basic quality
- **Pros:** Cheap, reliable, proven Linux support
- **Cons:** 16-bit only (still CD quality)
- **Verdict:** Good for proof of concept, adequate for most vinyl

### Professional: Focusrite Scarlett Solo ($120)
- **Specs:** 24-bit / 192 kHz
- **ADC:** High-quality converters
- **Pros:** Excellent preamps, professional build
- **Cons:** More expensive, USB bus-powered
- **Verdict:** Best quality, overkill for this project

### Raspberry Pi HAT: HiFiBerry DAC+ ADC Pro ($65)
- **Specs:** 24-bit / 192 kHz
- **Connection:** I2S (direct to Pi, no USB)
- **ADC:** Premium converters (PCM1863)
- **Pros:** Integrated, low latency, excellent quality
- **Cons:** Pi-specific, not USB (won't work on this Linux machine for testing)
- **Verdict:** Best for final Pi deployment

## Quality Preservation Chain

### The Weakest Link Principle
Audio quality is limited by the **worst component** in the chain:

```
Turntable → Preamp → USB Interface → Digital Capture → Encoding → Network → Sonos DAC → Speaker
```

**Each stage must maintain quality:**
1. **Turntable cartridge:** Decent quality needed (Audio-Technica AT-LP120 or better)
2. **Preamp:** Built-in or external phono preamp
3. **USB Interface:** 16-bit minimum, 24-bit preferred
4. **Capture:** Proper levels (avoid clipping), low noise floor
5. **Encoding:** ALAC lossless ✓
6. **Network:** Stable connection ✓
7. **Sonos DAC:** High-quality ✓
8. **Speaker quality:** Sonos Beam is good ✓

**TurnTabler's responsibility:** Steps 4-6 (capture, encoding, network)

## Quality Metrics to Measure

### Signal-to-Noise Ratio (SNR)
**What it is:** Ratio of desired audio to background noise

- **Good:** >90 dB
- **Excellent:** >100 dB
- **Vinyl typical:** 60-70 dB (surface noise is inherent)

**How to measure:** Record silence, analyze noise floor in Audacity/FFT

### Total Harmonic Distortion (THD)
**What it is:** Measure of unwanted harmonic content

- **Good:** <0.1%
- **Excellent:** <0.01%

**For TurnTabler:** Likely dominated by turntable/vinyl itself, not digital chain

### Frequency Response
**What it is:** How evenly different frequencies are reproduced

- **Ideal:** Flat 20 Hz - 20 kHz
- **Vinyl typical:** Some rolloff above 15 kHz (normal)

**How to verify:**
1. Generate test tones (20 Hz, 100 Hz, 1 kHz, 10 kHz, 20 kHz)
2. Stream through TurnTabler
3. Record output from Sonos (if possible) or listen critically

### Latency
**What it is:** Delay from input to output

- **AirPlay 2 typical:** 200-300ms
- **Acceptable for vinyl:** Anything <500ms (you're not interacting)

**How to measure:**
1. Play a transient sound (clap, drumbeat)
2. Measure time from source to Sonos output
3. Use high-speed camera or audio recording for precision

## Quality Validation Checklist

### Before Streaming
- [ ] Audio file is lossless format (FLAC, WAV, ALAC)
- [ ] Bit depth is 16-bit or 24-bit (no 8-bit!)
- [ ] Sample rate is 44.1 kHz or 48 kHz (no upsampling from 22 kHz sources)
- [ ] No clipping or distortion in source file

### During Streaming
- [ ] No audible artifacts (clicks, pops, dropouts)
- [ ] Volume level appropriate (not too quiet, not distorted)
- [ ] Stereo imaging correct (left/right not swapped)
- [ ] Network stable (no buffering interruptions)

### After Implementation
- [ ] Compare source file to Sonos output (A/B test)
- [ ] Verify ALAC codec being used (not AAC/MP3)
- [ ] Check spectral analysis (no high-frequency rolloff)
- [ ] Long-term stability (stream for 1 hour without issues)

## Common Quality Pitfalls to Avoid

### 1. Accidental Lossy Encoding
**Problem:** Accidentally encoding to AAC or MP3 instead of ALAC

**Prevention:**
- Explicitly specify ALAC codec in streaming tool
- Verify with Wireshark or tool logs
- Listen for compression artifacts

### 2. Sample Rate Conversion Issues
**Problem:** Poor-quality resampling introduces artifacts

**Solution:**
- Use high-quality resampler (SoX, FFmpeg's swresample)
- If source is 44.1 kHz, consider keeping it (don't upsample to 48 kHz unnecessarily)
- Let RAOP/AirPlay handle any necessary conversion

### 3. Clipping
**Problem:** Audio levels too high, causing distortion

**Prevention:**
- Set recording levels to peak at -6 dB (leave headroom)
- Use normalization if needed, but preserve dynamics
- Monitor input levels during turntable capture

### 4. Network Quality
**Problem:** WiFi congestion causes dropouts

**Solution:**
- Use Ethernet for both Pi and Sonos if possible
- Keep Pi and Sonos on same subnet (no router hops)
- Test during peak network usage times

### 5. Jitter/Timing Issues
**Problem:** Inconsistent streaming timing causes audio glitches

**Solution:**
- Use proper buffering (RAOP handles this)
- Ensure Pi isn't CPU-throttling (cooling, power supply)
- Avoid other heavy processes during streaming

## Testing Methodology

### Phase 1: File Streaming Quality Test
1. **Prepare test files:**
   - 16-bit/44.1kHz WAV (CD quality baseline)
   - 24-bit/48kHz FLAC (target quality)
   - Known reference tracks (audiophile recordings)

2. **Stream through TurnTabler**

3. **Subjective evaluation:**
   - Listen on Sonos Beam
   - Compare to direct playback (Sonos app playing same file)
   - Note any audible differences

4. **Objective measurement:**
   - Verify ALAC codec via logs/Wireshark
   - Check latency (acceptable <500ms)
   - Monitor network bandwidth usage

### Phase 2: Live Input Quality Test (Future)
1. **Capture from USB audio interface**
2. **Real-time streaming to Sonos**
3. **Compare to direct turntable listening** (if possible)

### Documentation
Record results in `/docs/implementation/quality-report.md`

## References

- [Nyquist-Shannon Sampling Theorem](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem) - Why 48 kHz captures up to 24 kHz
- [ALAC Codec Details](https://alac.macosforge.org/)
- [Audio Bit Depth Explained](https://www.sweetwater.com/insync/what-is-bit-depth/)
- [Vinyl Frequency Response](https://www.analogplanet.com/content/vinyl-frequency-response-facts-and-fiction)
