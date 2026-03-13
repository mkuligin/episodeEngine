import json

from agent.context_builder import ContextBuilder
from llm.model_interface import MockModel
from runtime.episode import EpisodeRuntime
from tools.tool_runner import ToolRunner
from utils.schemas import ExecutionResult, Step, Task


class Executor:
    def __init__(self, model: MockModel, context_builder: ContextBuilder, tool_runner: ToolRunner):
        self.model = model
        self.context_builder = context_builder
        self.tool_runner = tool_runner

    def execute(self, task: Task, runtime: EpisodeRuntime, step: Step) -> tuple[dict, ExecutionResult]:
        prompt = self.context_builder.step_prompt(task, runtime, step, runtime.confirmed_facts)
        action = self._parse_action(self.model.generate(prompt))
        return action, self.tool_runner.run(action)

    def _parse_action(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise
