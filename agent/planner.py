from utils.schemas import Step


class Planner:
    def parse(self, text: str) -> list[Step]:
        steps = []
        for idx, raw in enumerate(line for line in text.splitlines() if line.strip()):
            description = raw.split(".", 1)[-1].strip()
            lowered = description.lower()
            if "inspect" in lowered:
                action_type = "list_dir"
            elif "fix" in lowered:
                action_type = "write_file"
            else:
                action_type = "shell"
            steps.append(
                Step(
                    id=f"step-{idx + 1}",
                    description=description,
                    action_type=action_type,
                    dependencies=[f"step-{idx}"] if idx else [],
                )
            )
        return steps
