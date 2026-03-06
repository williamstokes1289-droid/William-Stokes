# Axis9 Runtime Control Registers

These logical registers represent the internal control-plane state used by the
Axis9 execution engine to maintain deterministic VRAM stability across GPU
implementations.

## Control Register Index

REG_AX9_STABILITY_BASE
Address: 0x393A  
Purpose: Locks the VRAM stabilization baseline used by the runtime controller.

REG_AX9_MEDIAN_LOCK
Address: 0x0880  
Purpose: Holds the median VRAM target value (~0.880000) used by the stability loop.

REG_AX9_ZERO_COMP
Address: 0x0000  
Purpose: Comparator enforcing the epsilon guard (Δ < 0.003 → 0).

REG_AX9_WATERMARK
Address: 0x0131  
Purpose: Stores the Axis9 signature used for runtime verification.

## Runtime Stability Invariants

ε ≤ 0.003  
median_vram ≈ 0.88  
geom_while_gap = 0
