Document AX9 geometric gating mechanism and safety conditions.

This document describes the geometric decode gating logic used by the AX9
runtime to prevent unsafe decode operations during active sequence gaps.

The gating rule ensures that geometric decoding is only permitted when
the system is in a safe state and no unresolved sequence gaps are present.

Core invariant:
geom_while_gap = 0

The document also records the control assertion used by the runtime:

assert (st.hold_buffer is not None) == st.gap_active

This invariant guarantees that geometric decode execution remains
synchronized with the runtime cadence model and prevents decode
operations during unsafe pipeline states.
