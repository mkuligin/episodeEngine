from pathlib import Path

from agent.orchestrator import Orchestrator
from llm.model_interface import build_model
from memory.episode_store import EpisodeStore
from memory.retrieval import RetrievalEngine
from runtime.event_journal import EventJournal
from tools.tool_runner import ToolRunner
from utils.schemas import Task


def build_demo_project(root: Path) -> Path:
    project_dir = root / "demo_project"
    project_dir.mkdir(exist_ok=True)
    (project_dir / "calculator.py").write_text(
        "def add(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (project_dir / "test_calculator.py").write_text(
        "import unittest\n\n"
        "from calculator import add\n\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
        encoding="utf-8",
    )
    return project_dir


def main() -> None:
    root = Path(__file__).parent
    project_dir = build_demo_project(root)
    storage_dir = root / "storage"
    orchestrator = Orchestrator(
        state_manager=None,
        context_builder=None,
        planner=None,
        executor=None,
        verifier=None,
        journal=EventJournal(storage_dir / "events.jsonl"),
        store=EpisodeStore(storage_dir),
        retrieval=RetrievalEngine(storage_dir),
        model=build_model(),
        tool_runner=ToolRunner(project_dir),
        workspace=project_dir,
    )
    task = Task(
        id="task-1",
        description="Fix failing unit tests in project",
        project="demo",
        completion_criteria="tests pass",
    )
    print(orchestrator.run(task))


if __name__ == "__main__":
    main()
