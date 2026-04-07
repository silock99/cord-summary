from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PlayerEntry:
    name: str
    position: str
    school: str
    stars: int  # 0 for unrated, 1-5 for rated
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position,
            "school": self.school,
            "stars": self.stars,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        return cls(**data)
