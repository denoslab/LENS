"""Configuration data structures and loaders for rubric and role definitions.

The pipeline requires two JSON config files:
  - ``config/lens_rubric.json``: defines the 8 evaluation dimensions
  - ``config/roles.json``: defines the 3 clinical roles with per-dimension
    weight vectors (``w_prior``) and optional LLM prompt profile paths

This module parses those files into frozen dataclasses used throughout
the scoring and orchestration layers.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class Dimension:
    """A single rubric evaluation dimension (e.g. "factual_accuracy")."""

    id: str
    name: str
    definition: str
    evaluation_focus: str


@dataclass(frozen=True)
class Rubric:
    """The full evaluation rubric containing all scoring dimensions."""

    rubric_id: str
    dimensions: List[Dimension]

    @property
    def dimension_ids(self) -> List[str]:
        """Return ordered list of dimension ID strings."""
        return [d.id for d in self.dimensions]


@dataclass(frozen=True)
class RoleProfile:
    """A clinical role's configuration: identity, weights, and LLM profile.

    Attributes:
        id: Machine-readable identifier (e.g. "physician", "triage_nurse").
        name: Human-readable role name.
        persona: One-line persona description used in LLM prompts.
        w_prior: Per-dimension importance weights, each in [0, 1].
        prompt_profile: Optional LLM-specific scoring profile loaded from
            a separate JSON file (empty dict if not provided).
    """

    id: str
    name: str
    persona: str
    w_prior: Dict[str, float]
    prompt_profile: Dict[str, Any]


def load_rubric(path: str | Path) -> Rubric:
    """Load and parse a rubric JSON file into a ``Rubric`` instance."""
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
    """Load a role's LLM prompt profile JSON from disk.

    The ``profile_path`` field in the role config is relative to the
    directory containing ``roles.json``.  Returns an empty dict if no
    profile path is specified.

    Raises:
        ValueError: If the profile file is missing or contains invalid JSON.
    """
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
    """Ensure all weight values are finite, in [0, 1], and not all zero.

    Raises:
        ValueError: On NaN/inf, out-of-range, or all-zero weights.
    """
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
    """Load role definitions from JSON, validating weights against the rubric.

    Args:
        path: Path to ``roles.json``.
        dimension_ids: Expected dimension IDs from the rubric, used to
            detect missing or extraneous weight keys.

    Returns:
        List of ``RoleProfile`` instances, one per role in the config.

    Raises:
        ValueError: On missing/extra dimension weights or invalid weight values.
    """
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
