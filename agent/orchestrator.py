from datetime import UTC, datetime
from pathlib import Path

from agent.context_builder import ContextBuilder
from agent.executor import Executor
from agent.planner import Planner
from agent.state_manager import StateManager
from agent.verifier import Verifier
from llm.model_interface import MockModel
from memory.episode_store import EpisodeStore
from memory.retrieval import RetrievalEngine
from runtime.episode import EpisodeRuntime
from runtime.event_journal import EventJournal
from tools.tool_runner import ToolRunner
from utils.schemas import EpisodeCard, Event, Step, Task


class Orchestrator:
    def __init__(
        self,
        state_manager: StateManager | None,
        context_builder: ContextBuilder | None,
        planner: Planner | None,
        executor: Executor | None,
        verifier: Verifier | None,
        journal: EventJournal,
        store: EpisodeStore,
        retrieval: RetrievalEngine,
        model: MockModel,
        tool_runner: ToolRunner,
        workspace: Path,
    ):
        self.state_manager = state_manager or StateManager()
        self.context_builder = context_builder or ContextBuilder()
        self.planner = planner or Planner()
        self.executor = executor or Executor(model, self.context_builder, tool_runner)
        self.verifier = verifier or Verifier(workspace)
        self.journal = journal
        self.store = store
        self.retrieval = retrieval
        self.model = model
        self.workspace = workspace
        self.max_attempts = 6

    def run(self, task: Task) -> str:
        runtime = self._register(task)
        self._initialize(task, runtime)
        self._plan(task, runtime)
        self._execute_loop(task, runtime)
        return self._close(task, runtime)

    def _register(self, task: Task) -> EpisodeRuntime:
        episode_id = f"episode-{task.id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        runtime = self.state_manager.create_episode_state(task, episode_id)
        self._log(runtime, "", "episode_registered", {"task": task.description})
        return runtime

    def _initialize(self, task: Task, runtime: EpisodeRuntime) -> None:
        retrieved = self.retrieval.retrieve(task, self.workspace)
        self.state_manager.confirm_fact(runtime, f"project={task.project}")
        for fact in retrieved["environment_facts"]:
            self.state_manager.confirm_fact(runtime, fact)
        if retrieved["similar_episodes"]:
            self.state_manager.confirm_fact(runtime, "memory_hint=similar episodes found")
        self.state_manager.set_phase(runtime, "plan")
        self._log(runtime, "", "retrieval_complete", retrieved)

    def _plan(self, task: Task, runtime: EpisodeRuntime) -> None:
        prompt = self.context_builder.planning_prompt(task, runtime, runtime.confirmed_facts)
        plan_text = self.model.generate(prompt)
        steps = self.planner.parse(plan_text)
        self.state_manager.set_steps(runtime, steps)
        self.state_manager.update_summary(runtime, f"Plan created with {len(steps)} steps")
        self.state_manager.set_phase(runtime, "execute")
        self._log(runtime, "", "plan_created", {"steps": [step.description for step in steps]})

    def _execute_loop(self, task: Task, runtime: EpisodeRuntime) -> None:
        while runtime.episode.attempt_counter < self.max_attempts:
            step = self._select_step(runtime)
            if not step:
                runtime.episode.status = "completed"
                break
            if self._detect_loop(runtime, step):
                runtime.episode.status = "blocked"
                runtime.episode.phase = "loop_detected"
                self.state_manager.update_summary(runtime, "Loop detected, stopping episode")
                break
            self.state_manager.increment_attempts(runtime)
            self.state_manager.set_current_step(runtime, step.id)
            action, result = self.executor.execute(task, runtime, step)
            self._log(
                runtime,
                step.id,
                "step_executed",
                {"action": action, "result": result.__dict__},
            )
            ok, note = self.verifier.verify(step, result, runtime)
            if ok:
                self.state_manager.mark_complete(runtime, step.id)
                self.state_manager.confirm_fact(runtime, note)
                self.state_manager.update_summary(runtime, f"{step.description}: success")
                self._log(runtime, step.id, "step_verified", {"note": note})
                if "tests pass" in task.completion_criteria and "OK" in result.output:
                    runtime.episode.status = "completed"
                    break
            else:
                runtime.last_error = note
                self.state_manager.update_summary(runtime, f"{step.description}: failed - {note}")
                self._log(runtime, step.id, "step_failed", {"note": note})
        if runtime.episode.status == "active":
            runtime.episode.status = "max_attempts_reached"

    def _select_step(self, runtime: EpisodeRuntime) -> Step | None:
        for step in runtime.steps:
            ready = all(dep in runtime.completed_steps for dep in step.dependencies)
            if ready and step.id not in runtime.completed_steps:
                return step
        return None

    def _detect_loop(self, runtime: EpisodeRuntime, step: Step) -> bool:
        recent = [
            event
            for event in self.journal.recent_events(8)
            if event["episode_id"] == runtime.episode.id
        ]
        repeated = [e for e in recent if e["step_id"] == step.id and e["type"] == "step_failed"]
        same_error = len(repeated) >= 2 and all(
            e["payload"]["note"] == runtime.last_error for e in repeated
        )
        no_progress = len(repeated) >= 2
        if same_error or no_progress:
            runtime.loop_warnings += 1
        return runtime.loop_warnings > 0

    def _close(self, task: Task, runtime: EpisodeRuntime) -> str:
        runtime.episode.phase = "closure"
        card = EpisodeCard(
            goal=task.description,
            symptoms=[obs for obs in runtime.observations if "failed" in obs][:2],
            tested_hypotheses=["repository state inspected", "tests reveal status"],
            actions=[step.description for step in runtime.steps],
            outcome=runtime.episode.status,
            artifacts=sorted({*runtime.confirmed_facts, *runtime.completed_steps}),
        )
        self.store.store_card(runtime.episode.id, card)
        self.store.archive_episode(runtime)
        self._log(runtime, "", "episode_closed", {"status": runtime.episode.status})
        next_actions = (
            "None. Completion criteria satisfied."
            if runtime.episode.status == "completed"
            else "Inspect unresolved failure and plan another episode."
        )
        return (
            "Episode Summary\n"
            "---------------\n\n"
            f"Goal:\n{task.description}\n\n"
            f"What was done:\n{runtime.episode.working_summary}\n\n"
            f"Confirmed facts:\n- " + "\n- ".join(runtime.confirmed_facts) + "\n\n"
            f"Next actions:\n{next_actions}\n"
        )

    def _log(self, runtime: EpisodeRuntime, step_id: str, event_type: str, payload: dict) -> None:
        self.journal.append(
            Event(
                timestamp=datetime.now(UTC).isoformat(),
                episode_id=runtime.episode.id,
                step_id=step_id,
                type=event_type,
                payload=payload,
            )
        )
