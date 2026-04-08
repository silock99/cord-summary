from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PlayerEntry:
    name: str
    position: str
    school: str
    stars: int  # 0 for unrated, 1-5 for rated
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: str = "target"  # Player type: "target" or "outgoing" (Phase 8)
    stats: dict | None = None  # Career stats data (Phase 9)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "position": self.position,
            "school": self.school,
            "stars": self.stars,
            "added_at": self.added_at,
            "type": self.type,
        }
        if self.stats is not None:
            d["stats"] = self.stats
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
