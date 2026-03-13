from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agent.orchestrator import Orchestrator
from llm.model_interface import build_model
from memory.episode_store import EpisodeStore
from memory.retrieval import RetrievalEngine
from runtime.event_journal import EventJournal
from tools.tool_runner import ToolRunner
from utils.config import load_app_config
from utils.logging_config import setup_logging
from utils.schemas import Task


def _read_system_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _task_id() -> str:
    return datetime.now().strftime("task-%Y%m%d-%H%M%S")


def _render_routes(console: Console, model) -> None:
    table = Table(title="Model Routes")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Provider", style="green")
    table.add_column("Model", style="magenta")
    table.add_column("Configured")
    table.add_column("Active")
    for index, route in enumerate(model.describe_routes(), start=1):
        table.add_row(
            str(index),
            route["provider"],
            route["model"],
            route["configured"],
            route["active"],
        )
    console.print(table)


def _render_help(console: Console) -> None:
    console.print(
        Panel.fit(
            "/help\n"
            "/exit\n"
            "/models\n"
            "/mode auto|manual\n"
            "/use <provider> <model>\n"
            "/prompt",
            title="Commands",
            border_style="blue",
        )
    )


def main() -> None:
    root = Path(__file__).parent
    config = load_app_config(root)
    session_log = setup_logging(config.log_dir)
    console = Console()
    system_prompt = _read_system_prompt(config.system_prompt_file)
    model = build_model(config, system_prompt)

    orchestrator = Orchestrator(
        state_manager=None,
        context_builder=None,
        planner=None,
        executor=None,
        verifier=None,
        journal=EventJournal(config.storage_dir / "events.jsonl"),
        store=EpisodeStore(config.storage_dir),
        retrieval=RetrievalEngine(config.storage_dir),
        model=model,
        tool_runner=ToolRunner(config.workspace_dir),
        workspace=config.workspace_dir,
    )
    orchestrator.max_attempts = config.max_attempts

    console.print(
        Panel.fit(
            f"[bold]{config.app_name}[/bold]\n"
            f"Workspace: {config.workspace_dir}\n"
            f"System prompt: {config.system_prompt_file}\n"
            f"Router mode: {model.mode}\n"
            f"Active route: {model.active_route_label}\n"
            f"Session log: {session_log}",
            title="Startup",
            border_style="green",
        )
    )
    _render_help(console)
    _render_routes(console, model)

    while True:
        user_input = Prompt.ask("[bold cyan]episode-engine[/bold cyan]").strip()
        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/help":
            _render_help(console)
            continue
        if user_input == "/models":
            _render_routes(console, model)
            continue
        if user_input == "/prompt":
            console.print(Panel(system_prompt, title="System Prompt", border_style="yellow"))
            continue
        if user_input.startswith("/mode "):
            mode = user_input.split(maxsplit=1)[1]
            try:
                model.set_mode(mode)
            except ValueError as exc:
                console.print(f"[red]{exc}[/red]")
                continue
            console.print(f"[green]Router mode set to[/green] {mode}")
            continue
        if user_input.startswith("/use "):
            parts = user_input.split(maxsplit=2)
            if len(parts) != 3:
                console.print("[red]Usage:[/red] /use <provider> <model>")
                continue
            model.set_manual_route(parts[1], parts[2])
            console.print(f"[green]Active route:[/green] {model.active_route_label}")
            continue

        task = Task(
            id=_task_id(),
            description=user_input,
            project=config.workspace_dir.name,
            completion_criteria="Complete the task safely and leave the workspace in a usable state.",
        )
        try:
            with console.status(f"Running {task.id} via {model.active_route_label}"):
                summary = orchestrator.run(task)
        except Exception as exc:
            console.print(Panel(str(exc), title="Execution Error", border_style="red"))
            continue
        console.print(Panel(summary, title=task.id, border_style="green"))


if __name__ == "__main__":
    main()
