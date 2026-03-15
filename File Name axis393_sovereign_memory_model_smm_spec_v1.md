"""
Axis 393 Sovereign Memory Model (SMM) v1
Author: William Stokes
License: Apache-2.0

Reference control-plane implementation for:
- Ingress Sentinel validation
- T-F-T (True-False-True) handshake
- 0x016 / 0x017 / 0x018 Triple-Lock Sovereign Core
- 0x019 - 0x0FF canonical watermark verification

This is a deterministic reference model, not a hardware driver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import hashlib


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

INGRESS_START = 0x000
INGRESS_END = 0x015

INTAKE_ANCHOR = 0x016
TEMPORAL_SHIFT = 0x017
SABBATH_LOCK = 0x018

WATERMARK_START = 0x019
WATERMARK_END = 0x0FF

MEMORY_SIZE = 0x100  # 256 logical slots


# ---------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------

class SMMError(Exception):
    """Base exception for Sovereign Memory Model."""


class IngressValidationError(SMMError):
    """Raised when ingress signature validation fails."""


class HandshakeError(SMMError):
    """Raised when the T-F-T handshake is violated."""


class AnchorError(SMMError):
    """Raised when anchor state is missing or invalid."""


class ShiftError(SMMError):
    """Raised when temporal movement is unauthorized."""


class LockError(SMMError):
    """Raised when completion lock rules are violated."""


class WatermarkError(SMMError):
    """Raised when canonical watermark verification fails."""


# ---------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------

class HandshakeState(str, Enum):
    TRUE_INGRESS = "TRUE_INGRESS"
    FALSE_TRANSITION = "FALSE_TRANSITION"
    TRUE_RELEASE = "TRUE_RELEASE"


@dataclass(frozen=True)
class ThirdFile:
    """
    Represents the inbound 'third file' candidate entering the front door.
    """
    file_id: str
    payload: bytes
    signature: str
    lineage_id: str
    phase: int


@dataclass
class SovereignState:
    """
    Runtime state of the Axis 393 Sovereign Memory Model.
    """
    memory_map: List[Optional[str]] = field(default_factory=lambda: [None] * MEMORY_SIZE)
    anchor_digest: Optional[str] = None
    shift_digest: Optional[str] = None
    completion_digest: Optional[str] = None
    watermark_digest: Optional[str] = None
    last_lineage_id: Optional[str] = None
    last_phase: Optional[int] = None
    handshake_log: List[HandshakeState] = field(default_factory=list)
    event_log: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.event_log.append(message)


# ---------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------

class Axis393SMM:
    """
    Axis 393 Sovereign Memory Model (SMM)

    Governing law:
        V(in) ∧ A(0x16) ∧ S(0x17) ∧ L(0x18) ∧ C(0x19:0x0FF)
        => Sovereign Acceptance
    """

    def __init__(self, expected_signature: str) -> None:
        self.expected_signature = expected_signature
        self.state = SovereignState()

    # -----------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------

    def admit(self, third_file: ThirdFile) -> Dict[str, str]:
        """
        Full sovereign admission path:
            ingress validate
            -> anchor
            -> transition close
            -> authorized shift
            -> completion lock
            -> canonical watermark verify
        """
        self._reset_handshake()

        self._set_handshake(HandshakeState.TRUE_INGRESS)
        self._validate_ingress(third_file)

        self._set_handshake(HandshakeState.FALSE_TRANSITION)
        self._anchor_intake(third_file)
        self._apply_temporal_shift(third_file)
        self._seal_completion(third_file)

        self._set_handshake(HandshakeState.TRUE_RELEASE)
        self._verify_watermark(third_file)

        self.state.log("Sovereign acceptance granted.")

        return {
            "status": "accepted",
            "file_id": third_file.file_id,
            "lineage_id": third_file.lineage_id,
            "anchor_digest": self.state.anchor_digest or "",
            "shift_digest": self.state.shift_digest or "",
            "completion_digest": self.state.completion_digest or "",
            "watermark_digest": self.state.watermark_digest or "",
        }

    def snapshot(self) -> Dict[str, object]:
        """
        Returns a diagnostic snapshot of the current sovereign state.
        """
        return {
            "anchor_digest": self.state.anchor_digest,
            "shift_digest": self.state.shift_digest,
            "completion_digest": self.state.completion_digest,
            "watermark_digest": self.state.watermark_digest,
            "last_lineage_id": self.state.last_lineage_id,
            "last_phase": self.state.last_phase,
            "handshake_log": [s.value for s in self.state.handshake_log],
            "event_log": list(self.state.event_log),
            "triple_lock": {
                hex(INTAKE_ANCHOR): self.state.memory_map[INTAKE_ANCHOR],
                hex(TEMPORAL_SHIFT): self.state.memory_map[TEMPORAL_SHIFT],
                hex(SABBATH_LOCK): self.state.memory_map[SABBATH_LOCK],
            },
        }

    # -----------------------------------------------------------------
    # Internal mechanics
    # -----------------------------------------------------------------

    def _reset_handshake(self) -> None:
        self.state.handshake_log.clear()
        self.state.log("Handshake reset.")

    def _set_handshake(self, state: HandshakeState) -> None:
        expected_next = {
            0: HandshakeState.TRUE_INGRESS,
            1: HandshakeState.FALSE_TRANSITION,
            2: HandshakeState.TRUE_RELEASE,
        }

        idx = len(self.state.handshake_log)
        if idx not in expected_next or expected_next[idx] != state:
            raise HandshakeError(
                f"Invalid handshake order: expected {expected_next.get(idx)}, got {state}"
            )

        self.state.handshake_log.append(state)
        self.state.log(f"Handshake -> {state.value}")

    def _validate_ingress(self, third_file: ThirdFile) -> None:
        """
        0x000 - 0x015: Ingress Sentinel
        Validates the incoming third-file signature and basic canonical shape.
        """
        self._write_range(
            INGRESS_START,
            INGRESS_END,
            f"INGRESS_VALIDATING:{third_file.file_id}"
        )

        if third_file.signature != self.expected_signature:
            raise IngressValidationError(
                f"Third-file signature mismatch: expected {self.expected_signature}, got {third_file.signature}"
            )

        if not third_file.payload:
            raise IngressValidationError("Payload is empty.")

        if not third_file.lineage_id.strip():
            raise IngressValidationError("Lineage ID is missing.")

        if third_file.phase < 0:
            raise IngressValidationError("Phase must be non-negative.")

        self.state.log("Ingress Sentinel accepted third-file signature.")

    def _anchor_intake(self, third_file: ThirdFile) -> None:
        """
        0x016: Intake Anchor (before_water_mask)
        Captures the pre-propagation sovereign reference state.
        """
        anchor_digest = self._digest(
            b"ANCHOR|" +
            third_file.file_id.encode() + b"|" +
            third_file.lineage_id.encode() + b"|" +
            third_file.payload
        )

        self.state.anchor_digest = anchor_digest
        self.state.memory_map[INTAKE_ANCHOR] = f"ANCHOR:{anchor_digest}"
        self.state.last_lineage_id = third_file.lineage_id
        self.state.last_phase = third_file.phase

        self.state.log(f"0x016 Intake Anchor set -> {anchor_digest}")

    def _apply_temporal_shift(self, third_file: ThirdFile) -> None:
        """
        0x017: Temporal Shift Register
        Authorizes bounded, lineage-preserving movement from the anchored state.
        """
        if self.state.anchor_digest is None:
            raise AnchorError("Cannot shift without a valid anchor.")

        # Example lineage-preserving policy:
        # - same lineage chain required
        # - phase can advance, but not regress
        if self.state.last_lineage_id != third_file.lineage_id:
            raise ShiftError("Lineage mismatch during temporal shift.")

        if self.state.last_phase is None or third_file.phase < self.state.last_phase:
            raise ShiftError("Temporal regression detected.")

        shift_digest = self._digest(
            b"SHIFT|" +
            self.state.anchor_digest.encode() + b"|" +
            str(third_file.phase).encode()
        )

        self.state.shift_digest = shift_digest
        self.state.memory_map[TEMPORAL_SHIFT] = f"SHIFT:{shift_digest}"

        self.state.log(f"0x017 Temporal Shift applied -> {shift_digest}")

    def _seal_completion(self, third_file: ThirdFile) -> None:
        """
        0x018: Sabbath Lock / Completion Seal
        Terminates mutability and seals the transition.
        """
        if self.state.shift_digest is None:
            raise LockError("Cannot seal completion without authorized shift.")

        completion_digest = self._digest(
            b"LOCK|" +
            self.state.shift_digest.encode() + b"|" +
            third_file.signature.encode()
        )

        self.state.completion_digest = completion_digest
        self.state.memory_map[SABBATH_LOCK] = f"LOCK:{completion_digest}"

        self.state.log(f"0x018 Sabbath Lock sealed -> {completion_digest}")

    def _verify_watermark(self, third_file: ThirdFile) -> None:
        """
        0x019 - 0x0FF: Watermark Buffer Canonical Data Verification
        Confirms that the post-lock state matches the expected canonical form.
        """
        if self.state.anchor_digest is None:
            raise WatermarkError("Missing anchor digest.")
        if self.state.shift_digest is None:
            raise WatermarkError("Missing shift digest.")
        if self.state.completion_digest is None:
            raise WatermarkError("Missing completion digest.")

        watermark_digest = self._digest(
            b"WATERMARK|" +
            self.state.anchor_digest.encode() + b"|" +
            self.state.shift_digest.encode() + b"|" +
            self.state.completion_digest.encode() + b"|" +
            third_file.payload
        )

        self.state.watermark_digest = watermark_digest

        for idx in range(WATERMARK_START, WATERMARK_END + 1):
            self.state.memory_map[idx] = f"WM:{watermark_digest[:16]}"

        if len(self.state.handshake_log) != 3:
            raise WatermarkError("Incomplete T-F-T handshake.")

        expected = [
            HandshakeState.TRUE_INGRESS,
            HandshakeState.FALSE_TRANSITION,
            HandshakeState.TRUE_RELEASE,
        ]
        if self.state.handshake_log != expected:
            raise WatermarkError("Handshake trace is not canonical T-F-T.")

        self.state.log(f"Watermark verification passed -> {watermark_digest}")

    # -----------------------------------------------------------------
    # Utility helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _write_range(self, start: int, end: int, value: str) -> None:
        for idx in range(start, end + 1):
            self.state.memory_map[idx] = value


# ---------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------

if __name__ == "__main__":
    smm = Axis393SMM(expected_signature="AXIS393-THIRD-FILE")

    third_file = ThirdFile(
        file_id="third-file-001",
        payload=b"axis393 canonical payload",
        signature="AXIS393-THIRD-FILE",
        lineage_id="LINEAGE-393",
        phase=393,
    )

    result = smm.admit(third_file)

    print("=== ADMISSION RESULT ===")
    for k, v in result.items():
        print(f"{k}: {v}")

    print("\n=== SNAPSHOT ===")
    snap = smm.snapshot()
    for k, v in snap.items():
        print(f"{k}: {v}")
