"""Attention as a resource. (#27)"""
from __future__ import annotations
from ..dna.neurochem import BehaviorModulator, NeurochemState


class AttentionSystem:
    def __init__(self, neuro: NeurochemState) -> None:
        self.neuro = neuro
        self.focus: str = "idle"
        self.focus_depth: float = 0.0

    def distractibility(self) -> float:
        return BehaviorModulator(self.neuro).distractibility()

    def can_attend_to(self, new_stimulus: float) -> bool:
        threshold = self.focus_depth * (1.0 - self.distractibility())
        return new_stimulus > threshold

    def shift_focus(self, new_focus: str, depth: float) -> None:
        self.focus = new_focus
        self.focus_depth = max(0.0, min(1.0, depth))
        # focus shift consumes alertness
        self.neuro.norepinephrine = max(0.0, self.neuro.norepinephrine - 0.03)

    def relax(self) -> None:
        self.focus = "idle"
        self.focus_depth = max(0.0, self.focus_depth - 0.1)
