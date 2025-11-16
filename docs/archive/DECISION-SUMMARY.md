# Tech Stack Decision - Executive Summary

**Date:** 2025-11-14
**Status:** Research Complete - Ready for Implementation Decision

---

## The Critical Discovery

### AirPlay to Sonos = Lossy Audio ❌

**Research finding:**
AirPlay streams to Sonos are delivered as **AAC-LC (lossy codec)**, NOT lossless ALAC.

**This means:**
- Any AirPlay-based solution delivers lossy audio
- Defeats the project goal of lossless vinyl streaming
- Includes: VLC, GStreamer, PipeWire RAOP, OwnTone

**Evidence:**
- Multiple Sonos Community forum posts
- User reports confirming lossy delivery
- "For lossless on Sonos, must use Sonos app"

**See:** `/docs/research/sonos-native-vs-airplay.md`

---

## Two Viable Approaches

### Option 1: SoCo (Sonos Native Protocol) - LOSSLESS ✅

**What it is:**
Python library (SoCo) controlling Sonos via native UPnP protocol, streaming FLAC over HTTP

**Architecture:**
```
Turntable → USB Interface → Linux/Pi
  → Capture (ALSA)
  → Encode (FLAC real-time)
  → HTTP Server (Flask/FastAPI)
  → SoCo library (Python)
  → Sonos Native Protocol (UPnP)
  → Sonos Beam (FLAC lossless playback)
```

**Pros:**
- ✅ **TRUE LOSSLESS** - FLAC to Sonos
- ✅ Native Python library (SoCo)
- ✅ Simpler architecture
- ✅ 24-bit potential
- ✅ Easy installation (`pip install soco`)

**Cons:**
- ❌ Must implement HTTP streaming server
- ❌ Real-time FLAC encoding required
- ❌ Unknown latency (needs testing)
- ❌ Not purpose-built for turntables

**Confidence:** 8/10 (needs validation)

**Docs:** `/docs/implementation/soco-approach.md`

---

### Option 2: OwnTone (AirPlay 2) - LOSSY ❌

**What it is:**
Full music server with AirPlay 2 sender, designed for turntable streaming

**Architecture:**
```
Turntable → USB Interface → Linux/Pi
  → Named Pipe (FIFO)
  → OwnTone Server
  → AirPlay 2 Protocol
  → Sonos Beam (AAC-LC lossy)
```

**Pros:**
- ✅ Purpose-built for turntables
- ✅ Proven, mature solution
- ✅ Auto-detection of audio
- ✅ Multi-room AirPlay 2
- ✅ Web UI included

**Cons:**
- ❌ **LOSSY AUDIO** - AAC-LC to Sonos
- ❌ 16-bit maximum (pipe limitation)
- ❌ Heavyweight (full server)
- ❌ Complex installation
- ❌ No official Python library

**Confidence:** 9/10 (proven, but lossy)

**Docs:** `/docs/implementation/owntone-deep-dive.md`

---

## Comparison

| Aspect | SoCo (Native) | OwnTone (AirPlay) |
|--------|---------------|-------------------|
| **Audio Quality** | 🟢 FLAC lossless | 🔴 AAC-LC lossy |
| **Bit Depth** | 24-bit possible | 16-bit max |
| **Setup** | Medium | Complex |
| **Python** | 🟢 Native | JSON API |
| **Proven** | Unknown | 🟢 Yes |
| **Installation** | `pip install` | Build/PPA |

**For lossless quality:** SoCo is the only option

---

## Recommendation

### Phase 1: Validate SoCo (4-6 hours)

**Test these key questions:**
1. Does real-time HTTP FLAC streaming work?
2. What is the latency (acceptable < 1 sec)?
3. Is quality truly lossless?
4. Is it stable for long-term streaming?

**Steps:**
1. Install SoCo: `pip install soco`
2. Build simple Flask HTTP server
3. Test real-time FLAC encoding/streaming
4. Measure quality and latency
5. Test stability (1+ hour stream)

**Time to decision:** 1 day

---

### Decision Tree

```
START
  ↓
Test SoCo approach
  ↓
Does it work well?
  ├─ YES → Use SoCo
  │         • Better quality (lossless)
  │         • Simpler architecture
  │         • Native Python
  │
  └─ NO  → Use OwnTone
            • Accept lossy quality
            • Proven solution
            • Turnkey experience
```

**"Works well" means:**
- Latency < 1 second
- No frequent dropouts
- Quality is lossless
- Stable for hours

---

## Documentation Complete

All research findings documented:

### Research
- `/docs/research/sonos-native-vs-airplay.md` - Quality comparison
- `/docs/research/airplay-protocol.md` - AirPlay technical details
- `/docs/research/sender-vs-receiver.md` - Critical architectural distinction
- `/docs/research/audio-quality.md` - Lossless requirements

### Implementation
- `/docs/implementation/tech-stack-decision.md` - Full decision document
- `/docs/implementation/soco-approach.md` - SoCo detailed guide
- `/docs/implementation/owntone-deep-dive.md` - OwnTone detailed guide
- `/docs/implementation/PHASE1-CHECKLIST.md` - Implementation tasks

### Hardware
- `/docs/hardware/raspberry-pi-5-guide.md` - Pi deployment guide

### Project
- `/docs/linux-setup/audio-stack-options.md` - All options evaluated
- `claude.md` - Living project knowledge base

---

## Next Steps

**Immediate:**
1. Review this summary with user
2. Decide whether to test SoCo or go directly to OwnTone
3. Set up environment (Python 3.13 + uv)

**If testing SoCo:**
4. Phase 1A validation (4-6 hours)
5. Make final decision based on results

**If going straight to OwnTone:**
4. Accept lossy quality limitation
5. Begin OwnTone installation
6. Follow Phase 1 checklist

---

## Key Learnings

### 1. Most Linux AirPlay = Receivers
90% of Linux AirPlay tools make Linux a receiver (speaker), not sender. We need sender capability.

### 2. AirPlay ≠ Lossless on Sonos
Even though AirPlay 2 supports lossless, Sonos receives lossy AAC-LC. This is critical.

### 3. Sonos Native = True Lossless
Only Sonos's native UPnP protocol delivers true lossless (FLAC/ALAC).

### 4. Quality vs Convenience Trade-off
- **Best quality:** SoCo (lossless, more work)
- **Best convenience:** OwnTone (lossy, proven)

### 5. Same Code, Different Pi
Whatever we build on Ubuntu will run on Raspberry Pi with minimal changes.

---

## User Decision Required

**Question:** Should we test SoCo first (for lossless quality) or go directly to OwnTone (proven but lossy)?

**Recommendation:** Test SoCo first
- Only costs 4-6 hours
- If it works, we get lossless
- If it doesn't, we still have OwnTone

**Confidence in recommendation:** High (8/10)
