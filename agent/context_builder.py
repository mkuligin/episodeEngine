from runtime.episode import EpisodeRuntime
from utils.schemas import Step, Task


class ContextBuilder:
    def planning_prompt(self, task: Task, runtime: EpisodeRuntime, facts: list[str]) -> str:
        return (
            "PLANNING MODE\n"
            "Return exactly 4 numbered steps. Keep each step short.\n"
            "Use this flow: inspect, test, fix, re-test.\n"
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
            '{"tool":"shell","command":"python -m unittest"} '
            '{"tool":"write_file","path":"calculator.py","content":"def add(a, b):\\n    return a + b\\n"}\n'
            f"TASK: {task.description}\n"
            f"STEP: {step.description}\n"
            f"PHASE: {runtime.episode.phase}\n"
            f"SUMMARY: {runtime.episode.working_summary or 'none'}\n"
            f"FACTS: {'; '.join(facts) or 'none'}\n"
        )
