from pathlib import Path

from runtime.episode import EpisodeRuntime
from utils.schemas import ExecutionResult, Step


class Verifier:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def verify(self, step: Step, result: ExecutionResult, runtime: EpisodeRuntime) -> tuple[bool, str]:
        if "Run tests" in step.description or "Re-run tests" in step.description:
            output = result.output or result.errors
            if "OK" in output:
                return True, "tests pass"
            if "FAIL" in output:
                return True, "tests executed and exposed failure"
            return False, output or "tests did not run"
        if result.return_code != 0:
            return False, result.errors or "non-zero return code"
        if "Inspect repository" in step.description:
            return "calculator.py" in result.output, "repository inspected"
        if "Fix failing module" in step.description:
            text = (self.workspace / "calculator.py").read_text(encoding="utf-8")
            return "return a + b" in text, "calculator.py updated"
        return True, "step succeeded"
