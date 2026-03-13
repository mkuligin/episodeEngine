from pathlib import Path

from runtime.episode import EpisodeRuntime
from utils.schemas import ExecutionResult, Step


class Verifier:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def verify(self, step: Step, result: ExecutionResult, runtime: EpisodeRuntime) -> tuple[bool, str]:
        if result.return_code != 0:
            return False, result.errors or result.output or "non-zero return code"
        if step.action_type == "write_file":
            if result.changed_files:
                return True, f"updated {', '.join(result.changed_files)}"
            return False, "write_file reported no changed files"
        if step.action_type == "read_file":
            return bool(result.output.strip()), "file inspected"
        if step.action_type == "list_dir":
            return True, "workspace inspected"
        if "test" in step.description.lower():
            return True, "tests passed"
        return True, "command succeeded"
