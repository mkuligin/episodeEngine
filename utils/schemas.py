from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    description: str
    project: str
    completion_criteria: str


@dataclass
class Episode:
    id: str
    task_id: str
    status: str
    phase: str
    working_summary: str
    attempt_counter: int
    current_step: str = ""


@dataclass
class Step:
    id: str
    description: str
    action_type: str
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Event:
    timestamp: str
    episode_id: str
    step_id: str
    type: str
    payload: dict[str, Any]


@dataclass
class ExecutionResult:
    command: str
    return_code: int
    errors: str
    changed_files: list[str]
    duration: float
    output: str = ""


@dataclass
class EpisodeCard:
    goal: str
    symptoms: list[str]
    tested_hypotheses: list[str]
    actions: list[str]
    outcome: str
    artifacts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
