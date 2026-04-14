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
    jersey_number: int = 0  # 0 means unknown/not applicable
    class_year: str = ""  # "Fr.", "So.", "Jr.", "Sr.", "R-Fr.", "R-So.", "R-Jr.", "R-Sr." or empty

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "position": self.position,
            "school": self.school,
            "stars": self.stars,
            "added_at": self.added_at,
            "type": self.type,
        }
        d["jersey_number"] = self.jersey_number
        d["class_year"] = self.class_year
        if self.stats is not None:
            d["stats"] = self.stats
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TransferTarget:
    """Sheet-sourced basketball transfer target (Phase 13, D-14)."""

    name: str
    position: str = ""
    former_school: str = ""
    height_weight: str = ""
    ku_interest_level: str = ""
    made_contact: str = ""
    notes: str = ""
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position,
            "former_school": self.former_school,
            "height_weight": self.height_weight,
            "ku_interest_level": self.ku_interest_level,
            "made_contact": self.made_contact,
            "notes": self.notes,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TransferTarget":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
