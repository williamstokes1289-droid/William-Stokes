# Axis9 Thermal Control Registry

This document defines the logical telemetry and control registers used by the
Axis9 runtime stability controller. These fields represent the control-plane
state used for thermal feedback, VRAM monitoring, and fan regulation.

| Offset (Hex) | Registry Symbol | Bit Width | Functional Description |
|---------------|----------------|-----------|------------------------|
| 0x00 | T_BASE_JNC | 32-bit | Raw junction temperature (°C, fixed-point). |
| 0x04 | T_VRAM_BANK_0 | 32-bit | Primary VRAM module thermal sensor. |
| 0x08 | T_VRAM_BANK_1 | 32-bit | Secondary VRAM module thermal sensor. |
| 0x10 | HPG_PA_DAMP | 32-bit | Damping factor used by the stability controller. |
| 0x14 | HPG_PA_BIAS | 16-bit | Static power bias used to offset steady-state drift. |
| 0x20 | PWM_REQ_STATE | 8-bit | Commanded fan speed (0–255). |
| 0x21 | PWM_ACT_STATE | 8-bit | Actual fan speed from tachometer feedback. |

## Control Loop Role

The registry fields above feed the Axis9 stabilization loop:

Telemetry → Stability Controller → Fan / Power Adjustment

This control plane ensures thermal equilibrium and prevents drift
during sustained high-density compute workloads.
