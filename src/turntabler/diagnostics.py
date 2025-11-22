"""
Streaming diagnostics for TurnTabler.

Provides comprehensive metrics collection and analysis for debugging
and tuning audio streaming performance.
"""

import logging
import statistics
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StreamingDiagnostics:
    """
    Collects and analyzes streaming performance metrics.

    Enable with --debug flag to collect detailed metrics about chunk sizes,
    timing, and anomalies throughout the streaming pipeline.

    Usage:
        diagnostics = StreamingDiagnostics(enabled=True)
        diagnostics.record_chunk_read(size, latency)
        ...
        print(diagnostics.final_report())
    """

    enabled: bool = False
    summary_interval: int = 60  # Seconds between periodic summaries

    # Chunk metrics
    chunk_sizes: list[int] = field(default_factory=list)
    chunk_timestamps: list[float] = field(default_factory=list)

    # Timing metrics (in milliseconds)
    read_latencies: list[float] = field(default_factory=list)
    yield_latencies: list[float] = field(default_factory=list)
    thread_overheads: list[float] = field(default_factory=list)
    inter_yield_gaps: list[float] = field(default_factory=list)

    # Buffer occupancy tracking
    buffer_occupancies: list[int] = field(default_factory=list)

    # Anomaly tracking
    small_chunk_times: list[float] = field(default_factory=list)
    slow_read_times: list[float] = field(default_factory=list)
    slow_yield_times: list[float] = field(default_factory=list)
    large_gap_times: list[float] = field(default_factory=list)
    buffer_underrun_times: list[float] = field(default_factory=list)

    # Counters
    total_bytes: int = 0
    total_chunks: int = 0
    overruns: int = 0

    # Configuration (set during init)
    expected_chunk_size: int = 8192  # Expected bytes per chunk
    # Blocking mode takes ~42.7ms per period (2048 frames @ 48kHz)
    # Set thresholds with margin to avoid false positives
    slow_read_threshold_ms: float = 51.0  # Expected: 42.7ms, 20% margin
    slow_yield_threshold_ms: float = 100.0  # Higher tolerance for WiFi jitter
    small_chunk_threshold: int = 4096
    large_gap_threshold_ms: float = 100.0  # Higher tolerance for WiFi jitter
    buffer_underrun_threshold: int = 1  # Flag when buffer empty (occupancy < 1)

    # Timing
    start_time: float = 0.0
    last_summary_time: float = 0.0
    last_chunk_time: float = 0.0
    last_yield_time: float = 0.0

    def start(self):
        """Start diagnostics timing."""
        self.start_time = time.time()
        self.last_summary_time = self.start_time
        self.last_chunk_time = self.start_time

    def record_chunk_read(self, size: int, read_latency_ms: float):
        """
        Record a chunk read from ALSA.

        Args:
            size: Chunk size in bytes
            read_latency_ms: Time spent in pcm.read() in milliseconds
        """
        if not self.enabled:
            return

        now = time.time()
        elapsed = now - self.start_time

        self.chunk_sizes.append(size)
        self.chunk_timestamps.append(elapsed)
        self.read_latencies.append(read_latency_ms)
        self.total_bytes += size
        self.total_chunks += 1

        # Detect anomalies
        if size < self.small_chunk_threshold:
            self.small_chunk_times.append(elapsed)

        if read_latency_ms > self.slow_read_threshold_ms:
            self.slow_read_times.append(elapsed)

        self.last_chunk_time = now

    def record_yield(self, yield_latency_ms: float, thread_overhead_ms: float = 0.0):
        """
        Record a chunk yield to HTTP stream.

        Args:
            yield_latency_ms: Total time for yield operation
            thread_overhead_ms: Time spent in asyncio.to_thread
        """
        if not self.enabled:
            return

        now = time.time()
        elapsed = now - self.start_time

        self.yield_latencies.append(yield_latency_ms)
        if thread_overhead_ms > 0:
            self.thread_overheads.append(thread_overhead_ms)

        if yield_latency_ms > self.slow_yield_threshold_ms:
            self.slow_yield_times.append(elapsed)

        # Track inter-yield gap (time between successive yields)
        if self.last_yield_time > 0:
            gap_ms = (now - self.last_yield_time) * 1000
            self.inter_yield_gaps.append(gap_ms)
            if gap_ms > self.large_gap_threshold_ms:
                self.large_gap_times.append(elapsed)

        self.last_yield_time = now

    def record_buffer_occupancy(self, occupancy: int):
        """
        Record current buffer depth.

        Args:
            occupancy: Number of chunks currently in buffer
        """
        if not self.enabled:
            return

        self.buffer_occupancies.append(occupancy)

        if occupancy < self.buffer_underrun_threshold:
            elapsed = time.time() - self.start_time
            self.buffer_underrun_times.append(elapsed)

    def record_overrun(self):
        """Record an ALSA buffer overrun."""
        if not self.enabled:
            return
        self.overruns += 1

    def should_print_summary(self) -> bool:
        """Check if it's time to print a periodic summary."""
        if not self.enabled:
            return False
        now = time.time()
        return (now - self.last_summary_time) >= self.summary_interval

    def periodic_summary(self) -> str:
        """
        Generate periodic summary of recent metrics.

        Returns:
            Formatted summary string
        """
        if not self.enabled or not self.chunk_sizes:
            return ""

        now = time.time()
        elapsed = now - self.start_time
        interval = now - self.last_summary_time
        self.last_summary_time = now

        # Calculate rates
        rate_kbps = (self.total_bytes / elapsed) / 1000 if elapsed > 0 else 0

        # Recent anomalies (in last interval)
        recent_small = sum(
            1 for t in self.small_chunk_times if t > (elapsed - interval)
        )
        recent_slow_read = sum(
            1 for t in self.slow_read_times if t > (elapsed - interval)
        )
        recent_slow_yield = sum(
            1 for t in self.slow_yield_times if t > (elapsed - interval)
        )
        recent_large_gap = sum(
            1 for t in self.large_gap_times if t > (elapsed - interval)
        )

        # Only count buffer underruns as anomalies if yields are also slow
        # (otherwise it's just normal synchronized producer/consumer operation)
        slow_yield_pct = len(self.slow_yield_times) / len(self.yield_latencies) * 100 if self.yield_latencies else 0
        recent_underrun = 0
        if slow_yield_pct > 5:
            recent_underrun = sum(
                1 for t in self.buffer_underrun_times if t > (elapsed - interval)
            )

        total_anomalies = recent_small + recent_slow_read + recent_slow_yield + recent_large_gap + recent_underrun

        # Chunk size stats
        chunk_min = min(self.chunk_sizes) if self.chunk_sizes else 0
        chunk_avg = statistics.mean(self.chunk_sizes) if self.chunk_sizes else 0
        chunk_p99 = self._percentile(self.chunk_sizes, 99) if self.chunk_sizes else 0

        # Read latency stats
        read_avg = statistics.mean(self.read_latencies) if self.read_latencies else 0
        read_p99 = (
            self._percentile(self.read_latencies, 99) if self.read_latencies else 0
        )

        # Yield latency stats
        yield_avg = statistics.mean(self.yield_latencies) if self.yield_latencies else 0
        yield_p99 = (
            self._percentile(self.yield_latencies, 99) if self.yield_latencies else 0
        )

        lines = [
            f"=== Diagnostics ({int(elapsed)}s) ===",
            f"Chunks: {self.total_chunks:,} | Rate: {rate_kbps:.0f} KB/s | Anomalies: {total_anomalies}",
            f"Chunk sizes: min={chunk_min} avg={chunk_avg:.0f} p99={chunk_p99:.0f}",
            f"Latency (ms): read={read_avg:.1f} yield={yield_avg:.1f} p99_read={read_p99:.1f} p99_yield={yield_p99:.1f}",
        ]

        if total_anomalies > 0:
            details = []
            if recent_small > 0:
                details.append(f"{recent_small} small chunks")
            if recent_slow_read > 0:
                details.append(f"{recent_slow_read} slow reads")
            if recent_slow_yield > 0:
                details.append(f"{recent_slow_yield} slow yields")
            if recent_large_gap > 0:
                details.append(f"{recent_large_gap} large gaps")
            if recent_underrun > 0:
                details.append(f"{recent_underrun} buffer underruns")
            lines.append(f"Issues: {', '.join(details)}")

        return "\n".join(lines)

    def final_report(self) -> str:
        """
        Generate comprehensive final report.

        Returns:
            Formatted report string with all metrics and recommendations
        """
        if not self.enabled:
            return ""

        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return "No data collected"

        lines = [
            "",
            "=" * 60,
            "STREAMING DIAGNOSTICS REPORT",
            "=" * 60,
            "",
        ]

        # Overview
        expected_bytes = elapsed * 48000 * 2 * 2  # 48kHz, stereo, 16-bit
        actual_rate = self.total_bytes / elapsed
        expected_rate = 48000 * 2 * 2
        rate_accuracy = (actual_rate / expected_rate * 100) if expected_rate > 0 else 0

        lines.extend(
            [
                "Overview:",
                f"  Duration: {elapsed:.1f}s",
                f"  Total chunks: {self.total_chunks:,}",
                f"  Total bytes: {self.total_bytes / 1_000_000:.1f} MB",
                f"  Expected: {expected_bytes / 1_000_000:.1f} MB",
                f"  Throughput accuracy: {rate_accuracy:.1f}%",
                "",
            ]
        )

        # Chunk size distribution
        if self.chunk_sizes:
            size_buckets = {
                "<1024": 0,
                "1024-4095": 0,
                "4096-8191": 0,
                ">=8192": 0,
            }
            for size in self.chunk_sizes:
                if size < 1024:
                    size_buckets["<1024"] += 1
                elif size < 4096:
                    size_buckets["1024-4095"] += 1
                elif size < 8192:
                    size_buckets["4096-8191"] += 1
                else:
                    size_buckets[">=8192"] += 1

            lines.append("Chunk Size Distribution:")
            for bucket, count in size_buckets.items():
                pct = (count / len(self.chunk_sizes) * 100) if self.chunk_sizes else 0
                marker = (
                    " <-- PROBLEM"
                    if bucket in ["<1024", "1024-4095"] and count > 0
                    else ""
                )
                lines.append(f"  {bucket}: {count:,} ({pct:.1f}%){marker}")
            lines.append("")

        # Latency statistics
        if self.read_latencies:
            lines.append("Latency Statistics (ms):")
            lines.append("         min     p50     p95     p99     max")

            read_stats = self._get_stats(self.read_latencies)
            lines.append(
                f"  read   {read_stats['min']:6.2f}  {read_stats['p50']:6.2f}  "
                f"{read_stats['p95']:6.2f}  {read_stats['p99']:6.2f}  {read_stats['max']:6.2f}"
            )

            if self.yield_latencies:
                yield_stats = self._get_stats(self.yield_latencies)
                lines.append(
                    f"  yield  {yield_stats['min']:6.2f}  {yield_stats['p50']:6.2f}  "
                    f"{yield_stats['p95']:6.2f}  {yield_stats['p99']:6.2f}  {yield_stats['max']:6.2f}"
                )

            if self.thread_overheads:
                thread_stats = self._get_stats(self.thread_overheads)
                lines.append(
                    f"  thread {thread_stats['min']:6.2f}  {thread_stats['p50']:6.2f}  "
                    f"{thread_stats['p95']:6.2f}  {thread_stats['p99']:6.2f}  {thread_stats['max']:6.2f}"
                )

            if self.inter_yield_gaps:
                gap_stats = self._get_stats(self.inter_yield_gaps)
                lines.append(
                    f"  gap    {gap_stats['min']:6.2f}  {gap_stats['p50']:6.2f}  "
                    f"{gap_stats['p95']:6.2f}  {gap_stats['p99']:6.2f}  {gap_stats['max']:6.2f}"
                )

            lines.append("")

        # Buffer occupancy statistics
        if self.buffer_occupancies:
            buf_min = min(self.buffer_occupancies)
            buf_avg = statistics.mean(self.buffer_occupancies)
            buf_max = max(self.buffer_occupancies)
            lines.append("Buffer Occupancy:")
            lines.append(f"  min={buf_min} avg={buf_avg:.1f} max={buf_max}")
            lines.append("")

        # Anomalies
        lines.append("Anomalies:")
        lines.append(f"  ALSA overruns: {self.overruns}")
        lines.append(
            f"  Small chunks (<{self.small_chunk_threshold}): {len(self.small_chunk_times)}"
        )
        lines.append(
            f"  Slow reads (>{self.slow_read_threshold_ms}ms): {len(self.slow_read_times)}"
        )
        lines.append(
            f"  Slow yields (>{self.slow_yield_threshold_ms}ms): {len(self.slow_yield_times)}"
        )
        lines.append(
            f"  Large gaps (>{self.large_gap_threshold_ms}ms): {len(self.large_gap_times)}"
        )
        lines.append(
            f"  Buffer underruns (<{self.buffer_underrun_threshold}): {len(self.buffer_underrun_times)}"
        )

        # Show first few anomaly timestamps
        if self.small_chunk_times:
            times = [f"{t:.1f}s" for t in self.small_chunk_times[:5]]
            suffix = (
                f" (+{len(self.small_chunk_times) - 5} more)"
                if len(self.small_chunk_times) > 5
                else ""
            )
            lines.append(f"    Small chunk times: {', '.join(times)}{suffix}")

        if self.large_gap_times:
            times = [f"{t:.1f}s" for t in self.large_gap_times[:5]]
            suffix = (
                f" (+{len(self.large_gap_times) - 5} more)"
                if len(self.large_gap_times) > 5
                else ""
            )
            lines.append(f"    Large gap times: {', '.join(times)}{suffix}")

        if self.buffer_underrun_times:
            times = [f"{t:.1f}s" for t in self.buffer_underrun_times[:5]]
            suffix = (
                f" (+{len(self.buffer_underrun_times) - 5} more)"
                if len(self.buffer_underrun_times) > 5
                else ""
            )
            lines.append(f"    Buffer underrun times: {', '.join(times)}{suffix}")

        lines.append("")

        # Recommendations
        lines.append("Recommendations:")
        recommendations = self._generate_recommendations()
        if recommendations:
            for rec in recommendations:
                lines.append(f"  * {rec}")
        else:
            lines.append("  * No issues detected - streaming looks healthy!")

        lines.extend(["", "=" * 60, ""])

        return "\n".join(lines)

    def _generate_recommendations(self) -> list[str]:
        """Generate tuning recommendations based on collected metrics."""
        recs = []

        # Check for small chunks
        if self.chunk_sizes:
            small_count = sum(
                1 for s in self.chunk_sizes if s < self.small_chunk_threshold
            )
            small_pct = small_count / len(self.chunk_sizes) * 100
            if small_pct > 1:
                recs.append(
                    f"{small_pct:.1f}% small chunks - ALSA returning partial reads"
                )
                recs.append(
                    "Consider: Add buffering to accumulate full chunks before yielding"
                )
            elif small_pct > 0:
                recs.append(
                    f"{small_count} small chunks detected - minor partial reads"
                )
                recs.append("Consider: Increase period_size or switch to blocking mode")

        # Check for slow reads
        if self.read_latencies:
            slow_count = len(self.slow_read_times)
            if slow_count > 10:
                recs.append(
                    f"{slow_count} slow ALSA reads - possible system scheduling issues"
                )
                recs.append("Consider: Increase process priority or reduce system load")

        # Check for overruns
        if self.overruns > 0:
            recs.append(f"{self.overruns} ALSA overruns - capture buffer overflow")
            recs.append("Consider: Increase periods (ring buffer depth)")

        # Check for large inter-yield gaps
        if len(self.large_gap_times) > 0:
            gap_pct = len(self.large_gap_times) / len(self.inter_yield_gaps) * 100 if self.inter_yield_gaps else 0
            if gap_pct > 1:
                recs.append(f"{gap_pct:.1f}% large gaps - network or event loop delays")
                recs.append("Consider: Increase buffer depth to absorb jitter")
            else:
                recs.append(f"{len(self.large_gap_times)} large gaps detected - minor timing jitter")

        # Check for buffer underruns - only problematic if yields are also slow
        if len(self.buffer_underrun_times) > 0 and self.yield_latencies:
            # Calculate what % of yields were slow
            slow_yield_pct = len(self.slow_yield_times) / len(self.yield_latencies) * 100

            if slow_yield_pct > 5:
                # Real problem: buffer empty AND consumer waiting
                recs.append(f"{len(self.buffer_underrun_times)} buffer underruns with {slow_yield_pct:.1f}% slow yields")
                recs.append("Consider: Increase buffer size or check audio source")
            # Otherwise: buffer empty but yields fast = normal synchronized operation

        # Check throughput
        if self.total_bytes > 0 and self.start_time > 0:
            elapsed = time.time() - self.start_time
            actual_rate = self.total_bytes / elapsed
            expected_rate = 48000 * 2 * 2
            if actual_rate < expected_rate * 0.95:
                recs.append(
                    f"Throughput {actual_rate / expected_rate * 100:.1f}% of expected - data loss detected"
                )

        return recs

    def _percentile(self, data: list, percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def _get_stats(self, data: list) -> dict:
        """Get comprehensive statistics for a data series."""
        if not data:
            return {"min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

        return {
            "min": min(data),
            "max": max(data),
            "p50": self._percentile(data, 50),
            "p95": self._percentile(data, 95),
            "p99": self._percentile(data, 99),
        }
