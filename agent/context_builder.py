from runtime.episode import EpisodeRuntime
from utils.schemas import Step, Task


class ContextBuilder:
    def planning_prompt(self, task: Task, runtime: EpisodeRuntime, facts: list[str]) -> str:
        return (
            "PLANNING MODE\n"
            "Return JSON only. No markdown.\n"
            "Schema:\n"
            '{"steps":[{"description":"short action","action_type":"list_dir|read_file|write_file|shell","dependencies":["step-1"]}]}\n'
            "Plan 2 to 6 concrete steps for the current task.\n"
            "Use only supported action types.\n"
            "Prefer relative paths and deterministic shell commands.\n"
            f"TASK: {task.description}\n"
            f"CRITERIA: {task.completion_criteria}\n"
            f"PHASE: {runtime.episode.phase}\n"
            f"SUMMARY: {runtime.episode.working_summary or 'none'}\n"
            f"FACTS: {'; '.join(facts) or 'none'}\n"
        )

    def step_prompt(self, task: Task, runtime: EpisodeRuntime, step: Step, facts: list[str]) -> str:
        return (
            "EXECUTION MODE\n"
            "Return one JSON object only.\n"
            'Allowed formats: {"tool":"list_dir","path":"."} '
            '{"tool":"read_file","path":"relative/path.py"} '
            '{"tool":"shell","command":"python -m pytest tests/test_app.py"} '
            '{"tool":"write_file","path":"relative/path.py","content":"full file content"}\n'
            "Choose exactly one tool call for the current step.\n"
            "Paths must be relative to the workspace.\n"
            "For write_file, return the full file content.\n"
            f"TASK: {task.description}\n"
            f"STEP: {step.description}\n"
            f"ACTION TYPE: {step.action_type}\n"
            f"PHASE: {runtime.episode.phase}\n"
            f"SUMMARY: {runtime.episode.working_summary or 'none'}\n"
            f"FACTS: {'; '.join(facts) or 'none'}\n"
        )
