from dataclasses import dataclass, field
from typing import Any

from utils.schemas import Episode, Step


@dataclass
class EpisodeRuntime:
    episode: Episode
    steps: list[Step] = field(default_factory=list)
    completed_steps: set[str] = field(default_factory=set)
    observations: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    last_error: str = ""
    loop_warnings: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
