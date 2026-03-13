import json
import re

from utils.schemas import Step


class Planner:
    def parse(self, text: str) -> list[Step]:
        stripped = text.strip()
        if not stripped:
            return []
        if stripped.startswith("{") or stripped.startswith("["):
            parsed = self._parse_json_plan(stripped)
            if parsed:
                return parsed
        return self._parse_text_plan(stripped)

    def _parse_json_plan(self, text: str) -> list[Step]:
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            return []

        raw_steps = body.get("steps", body) if isinstance(body, dict) else body
        if not isinstance(raw_steps, list):
            return []

        steps: list[Step] = []
        for idx, item in enumerate(raw_steps):
            step_id = f"step-{idx + 1}"
            if isinstance(item, str):
                description = item.strip()
                action_type = self._infer_action_type(description)
                dependencies = [f"step-{idx}"] if idx else []
            else:
                description = str(item.get("description", "")).strip()
                action_type = str(item.get("action_type", "")).strip() or self._infer_action_type(
                    description
                )
                dependencies = self._normalize_dependencies(item.get("dependencies"), idx)
            if not description:
                continue
            steps.append(
                Step(
                    id=step_id,
                    description=description,
                    action_type=action_type,
                    dependencies=dependencies,
                )
            )
        return steps

    def _parse_text_plan(self, text: str) -> list[Step]:
        lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
        steps: list[Step] = []
        for idx, raw in enumerate(lines):
            description = re.sub(r"^\d+[.)]\s*", "", raw).strip()
            if not description:
                continue
            steps.append(
                Step(
                    id=f"step-{idx + 1}",
                    description=description,
                    action_type=self._infer_action_type(description),
                    dependencies=[f"step-{idx}"] if idx else [],
                )
            )
        return steps

    def _normalize_dependencies(self, value: object, idx: int) -> list[str]:
        if not value:
            return [f"step-{idx}"] if idx else []
        if not isinstance(value, list):
            return [f"step-{idx}"] if idx else []
        dependencies: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            if text.isdigit():
                dependencies.append(f"step-{text}")
            elif text.startswith("step-"):
                dependencies.append(text)
        return dependencies or ([f"step-{idx}"] if idx else [])

    def _infer_action_type(self, description: str) -> str:
        lowered = description.lower()
        if any(token in lowered for token in ("list", "inspect", "scan", "explore", "find", "tree")):
            return "list_dir"
        if any(token in lowered for token in ("read", "open", "review", "check file")):
            return "read_file"
        if any(
            token in lowered
            for token in ("write", "fix", "edit", "update", "create", "patch", "change")
        ):
            return "write_file"
        return "shell"
