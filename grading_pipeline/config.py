import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Dimension:
    id: str
    name: str
    definition: str
    evaluation_focus: str


@dataclass(frozen=True)
class Rubric:
    rubric_id: str
    dimensions: List[Dimension]

    @property
    def dimension_ids(self) -> List[str]:
        return [d.id for d in self.dimensions]


@dataclass(frozen=True)
class RoleProfile:
    id: str
    name: str
    persona: str
    w_prior: Dict[str, float]


def load_rubric(path: str | Path) -> Rubric:
    data = json.loads(Path(path).read_text())
    dims = [
        Dimension(
            id=item["id"],
            name=item["name"],
            definition=item["definition"],
            evaluation_focus=item["evaluation_focus"],
        )
        for item in data["dimensions"]
    ]
    return Rubric(rubric_id=data["rubric_id"], dimensions=dims)


def load_roles(path: str | Path, dimension_ids: List[str]) -> List[RoleProfile]:
    data = json.loads(Path(path).read_text())
    roles: List[RoleProfile] = []
    for item in data["roles"]:
        w_prior = item["w_prior"]
        missing = set(dimension_ids) - set(w_prior.keys())
        extra = set(w_prior.keys()) - set(dimension_ids)
        if missing:
            raise ValueError(
                f"Role {item['id']} missing weights for: {sorted(missing)}"
            )
        if extra:
            raise ValueError(
                f"Role {item['id']} has unknown dimensions: {sorted(extra)}"
            )
        roles.append(
            RoleProfile(
                id=item["id"],
                name=item["name"],
                persona=item["persona"],
                w_prior={k: float(v) for k, v in w_prior.items()},
            )
        )
    return roles
