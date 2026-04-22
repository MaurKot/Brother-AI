"""Anomaly detector — notices departures from baseline. (#41)"""
from __future__ import annotations
from typing import Dict, List


class AnomalyDetector:
    def __init__(self) -> None:
        self.baselines: Dict[str, float] = {}
        self.alpha = 0.05  # baseline EMA rate

    def update(self, metric: str, value: float) -> None:
        prev = self.baselines.get(metric, value)
        self.baselines[metric] = prev + self.alpha * (value - prev)

    def check(self, snapshot: Dict[str, float], threshold_ratio: float = 0.5) -> List[str]:
        alerts: List[str] = []
        for metric, value in snapshot.items():
            base = self.baselines.get(metric)
            if base is None:
                self.baselines[metric] = value
                continue
            denom = max(0.05, abs(base))
            if abs(value - base) / denom > threshold_ratio:
                alerts.append(f"{metric}={value:.2f} (база {base:.2f})")
            self.update(metric, value)
        return alerts
