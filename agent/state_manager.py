from runtime.episode import EpisodeRuntime
from utils.schemas import Episode, Step, Task


class StateManager:
    def create_episode_state(self, task: Task, episode_id: str) -> EpisodeRuntime:
        return EpisodeRuntime(
            episode=Episode(
                id=episode_id,
                task_id=task.id,
                status="active",
                phase="orient",
                working_summary="",
                attempt_counter=0,
            )
        )

    def set_phase(self, runtime: EpisodeRuntime, phase: str) -> None:
        runtime.episode.phase = phase

    def set_steps(self, runtime: EpisodeRuntime, steps: list[Step]) -> None:
        runtime.steps = steps

    def set_current_step(self, runtime: EpisodeRuntime, step_id: str) -> None:
        runtime.episode.current_step = step_id

    def increment_attempts(self, runtime: EpisodeRuntime) -> None:
        runtime.episode.attempt_counter += 1

    def update_summary(self, runtime: EpisodeRuntime, note: str) -> None:
        runtime.observations.append(note)
        runtime.episode.working_summary = " | ".join(runtime.observations[-3:])

    def confirm_fact(self, runtime: EpisodeRuntime, fact: str) -> None:
        if fact not in runtime.confirmed_facts:
            runtime.confirmed_facts.append(fact)

    def mark_complete(self, runtime: EpisodeRuntime, step_id: str) -> None:
        runtime.completed_steps.add(step_id)
