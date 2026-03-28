from __future__ import annotations

from dataclasses import dataclass

from .constants import COMPLEXITY_MAP


@dataclass
class AudienceSegment:
    name: str
    ratio: float
    audience_type: str
    complexity: str
    in_group: bool

    @property
    def complexity_factor(self) -> float:
        return COMPLEXITY_MAP.get(self.complexity, 1.0)


class ValidationError(Exception):
    pass
