import shlex
import subprocess
import sys
import time
import logging
from pathlib import Path

from utils.schemas import ExecutionResult

logger = logging.getLogger(__name__)


class ToolRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def run(self, action: dict) -> ExecutionResult:
        tool = action["tool"]
        start = time.perf_counter()
        logger.debug("ToolRunner received action: %s", action)
        if tool == "shell":
            command = action["command"]
            parts = shlex.split(command)
            if parts and parts[0] == "python":
                parts[0] = sys.executable
            proc = subprocess.run(
                parts,
                cwd=self.workspace,
                text=True,
                capture_output=True,
            )
            logger.debug("Shell command finished code=%s command=%s", proc.returncode, command)
            return ExecutionResult(
                command=command,
                return_code=proc.returncode,
                errors=proc.stderr.strip(),
                changed_files=[],
                duration=time.perf_counter() - start,
                output=proc.stdout.strip(),
            )
        if tool == "read_file":
            path = self.workspace / action["path"]
            logger.debug("Reading file %s", path)
            return ExecutionResult(
                command=f"read {action['path']}",
                return_code=0,
                errors="",
                changed_files=[],
                duration=time.perf_counter() - start,
                output=path.read_text(encoding="utf-8"),
            )
        if tool == "write_file":
            path = self.workspace / action["path"]
            logger.debug("Writing file %s", path)
            path.write_text(action["content"], encoding="utf-8")
            return ExecutionResult(
                command=f"write {action['path']}",
                return_code=0,
                errors="",
                changed_files=[action["path"]],
                duration=time.perf_counter() - start,
                output="file updated",
            )
        if tool == "list_dir":
            files = sorted(p.name for p in (self.workspace / action.get("path", ".")).iterdir())
            logger.debug("Listing directory %s", self.workspace / action.get("path", "."))
            return ExecutionResult(
                command=f"list {action.get('path', '.')}",
                return_code=0,
                errors="",
                changed_files=[],
                duration=time.perf_counter() - start,
                output="\n".join(files),
            )
        return ExecutionResult(
            command=tool,
            return_code=1,
            errors=f"unsupported tool: {tool}",
            changed_files=[],
            duration=time.perf_counter() - start,
            output="",
        )
