AX9 Execution Engine

Deterministic GPU runtime designed to stabilize VRAM residency
and eliminate allocator drift in large compute pipelines.

Core Architecture
• Cadence Scheduler (3 / 6 / 7 execution model)
• Commit-True ingestion pipeline
• Manifest-only data staging
• Gap-safe geometric decoder
• Adaptive VRAM governor
• LaunchKey execution control plane

Runtime Validation (NVML telemetry, 600s window)
median_vram ≈ 0.88
oscillation amplitude ↓ ≈63%
allocator drift ↓ ≈17×
safe_progress ≈ 99.84%

Decoder safety invariant
geom_while_gap = 0

Copyright © 2026 William Stokes
AX9 Execution Engine architecture authored by William Stokes.
