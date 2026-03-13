import json
from dataclasses import asdict
from pathlib import Path

from runtime.episode import EpisodeRuntime
from utils.schemas import EpisodeCard


class EpisodeStore:
    def __init__(self, root: Path):
        self.root = root
        self.cards_dir = root / "cards"
        self.archive_dir = root / "episodes"
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def store_card(self, episode_id: str, card: EpisodeCard) -> None:
        path = self.cards_dir / f"{episode_id}.json"
        path.write_text(json.dumps(card.to_dict(), indent=2), encoding="utf-8")

    def archive_episode(self, runtime: EpisodeRuntime) -> None:
        path = self.archive_dir / f"{runtime.episode.id}.json"
        payload = {
            "episode": asdict(runtime.episode),
            "steps": [asdict(step) for step in runtime.steps],
            "completed_steps": sorted(runtime.completed_steps),
            "observations": runtime.observations,
            "confirmed_facts": runtime.confirmed_facts,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_cards(self) -> list[dict]:
        cards = []
        for path in sorted(self.cards_dir.glob("*.json")):
            cards.append(json.loads(path.read_text(encoding="utf-8")))
        return cards
