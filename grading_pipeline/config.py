import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


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
    prompt_profile: Dict[str, Any]


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


def _load_prompt_profile(roles_path: Path, role_item: Dict[str, Any]) -> Dict[str, Any]:
    profile_path = role_item.get("profile_path")
    if not profile_path:
        return {}

    full_path = roles_path.parent / profile_path
    try:
        return json.loads(full_path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(
            f"Role {role_item.get('id', '<unknown>')} profile file not found: {full_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Role {role_item.get('id', '<unknown>')} profile file is invalid JSON: {full_path}"
        ) from exc


def _validate_weights(role_id: str, weights: Dict[str, float]) -> None:
    for dim_id, value in weights.items():
        if not math.isfinite(value):
            raise ValueError(
                f"Role {role_id} weight for '{dim_id}' is not a finite number: {value}"
            )
        if value < 0.0 or value > 1.0:
            raise ValueError(
                f"Role {role_id} weight for '{dim_id}' must be in [0, 1], got {value}"
            )

    if sum(weights.values()) <= 0.0:
        raise ValueError(
            f"Role {role_id} has all-zero weights. At least one dimension must be > 0."
        )


def load_roles(path: str | Path, dimension_ids: List[str]) -> List[RoleProfile]:
    roles_path = Path(path)
    data = json.loads(roles_path.read_text())

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

        normalized_weights = {k: float(v) for k, v in w_prior.items()}
        _validate_weights(item["id"], normalized_weights)

        roles.append(
            RoleProfile(
                id=item["id"],
                name=item["name"],
                persona=item["persona"],
                w_prior=normalized_weights,
                prompt_profile=_load_prompt_profile(roles_path, item),
            )
        )

    return roles
