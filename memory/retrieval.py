from pathlib import Path

from memory.episode_store import EpisodeStore
from utils.schemas import Task


class RetrievalEngine:
    def __init__(self, root: Path):
        self.store = EpisodeStore(root)

    def retrieve(self, task: Task, workspace: Path) -> dict:
        keywords = set(task.description.lower().split())
        similar = []
        for card in self.store.load_cards():
            haystack = " ".join(
                [card.get("goal", ""), *card.get("symptoms", []), *card.get("actions", [])]
            ).lower()
            if keywords & set(haystack.split()):
                similar.append(card)
        env_facts = [
            f"workspace={workspace}",
            f"python_files={len(list(workspace.glob('*.py')))}",
        ]
        return {"similar_episodes": similar[:2], "environment_facts": env_facts}
