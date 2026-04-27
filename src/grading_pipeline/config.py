"""Configuration data structures and loaders for rubric and role definitions.

The pipeline requires two JSON config files:
  - ``lens_rubric.json``: defines the 8 evaluation dimensions
  - ``roles.json``: defines the 3 clinical roles with per-dimension
    weight vectors (``w_prior``) and optional LLM prompt profile paths

This module parses those files into frozen dataclasses used throughout
the scoring and orchestration layers. The CLI can also load bundled default
copies of the same config from package resources when explicit paths are not
provided.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable, Dict, List


DEFAULTS_PACKAGE = "grading_pipeline.defaults"


@dataclass(frozen=True)
class Dimension:
    """A single rubric evaluation dimension (e.g. ``factual_accuracy``)."""

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
    """A clinical role's configuration: identity, weights, and LLM profile."""

    id: str
    name: str
    persona: str
    w_prior: Dict[str, float]
    prompt_profile: Dict[str, Any]


JsonLoader = Callable[[str], Dict[str, Any]]


def _load_json_file(path: str | Path, *, label: str) -> Dict[str, Any]:
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"{label} file not found: {file_path}") from exc
    except OSError as exc:
        raise ValueError(f"{label} file could not be read: {file_path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} file is invalid JSON: {file_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object: {file_path}")
    return data


def _load_json_resource(package_relative_path: str, *, label: str) -> Dict[str, Any]:
    resource = files(DEFAULTS_PACKAGE).joinpath(package_relative_path)
    try:
        raw = resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"Bundled {label.lower()} resource not found: {package_relative_path}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Bundled {label.lower()} resource is invalid JSON: {package_relative_path}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Bundled {label.lower()} resource must be a JSON object: {package_relative_path}"
        )
    return data


def _ensure_non_empty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _build_rubric(data: Dict[str, Any], *, source_label: str) -> Rubric:
    rubric_id = _ensure_non_empty_string(data.get("rubric_id"), label="rubric_id")
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"{source_label} must define a non-empty 'dimensions' list.")

    seen_ids: set[str] = set()
    parsed: List[Dimension] = []
    for index, item in enumerate(dimensions, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"{source_label} dimension #{index} must be a JSON object."
            )
        dim_id = _ensure_non_empty_string(item.get("id"), label=f"dimension #{index} id")
        if dim_id in seen_ids:
            raise ValueError(f"{source_label} contains duplicate dimension id: {dim_id}")
        seen_ids.add(dim_id)
        parsed.append(
            Dimension(
                id=dim_id,
                name=_ensure_non_empty_string(item.get("name"), label=f"dimension '{dim_id}' name"),
                definition=_ensure_non_empty_string(
                    item.get("definition"), label=f"dimension '{dim_id}' definition"
                ),
                evaluation_focus=_ensure_non_empty_string(
                    item.get("evaluation_focus"),
                    label=f"dimension '{dim_id}' evaluation_focus",
                ),
            )
        )

    return Rubric(rubric_id=rubric_id, dimensions=parsed)


def load_rubric(path: str | Path) -> Rubric:
    """Load and validate a rubric JSON file into a ``Rubric`` instance."""
    data = _load_json_file(path, label="Rubric")
    return _build_rubric(data, source_label=f"Rubric file {Path(path)}")


def load_default_rubric() -> Rubric:
    """Load the bundled default rubric shipped with the package."""
    data = _load_json_resource("lens_rubric.json", label="Rubric")
    return _build_rubric(data, source_label="Bundled default rubric")


def _load_prompt_profile_from_disk(roles_path: Path, role_item: Dict[str, Any]) -> Dict[str, Any]:
    profile_path = role_item.get("profile_path")
    if not profile_path:
        return {}

    if not isinstance(profile_path, str) or not profile_path.strip():
        raise ValueError(
            f"Role {role_item.get('id', '<unknown>')} profile_path must be a non-empty string."
        )

    full_path = roles_path.parent / profile_path
    data = _load_json_file(full_path, label=f"Role {role_item.get('id', '<unknown>')} profile")
    if not isinstance(data, dict):
        raise ValueError(
            f"Role {role_item.get('id', '<unknown>')} profile must be a JSON object: {full_path}"
        )
    return data


def _load_prompt_profile_from_package(role_item: Dict[str, Any]) -> Dict[str, Any]:
    profile_path = role_item.get("profile_path")
    if not profile_path:
        return {}

    if not isinstance(profile_path, str) or not profile_path.strip():
        raise ValueError(
            f"Role {role_item.get('id', '<unknown>')} profile_path must be a non-empty string."
        )

    normalized = profile_path.replace("\\", "/").lstrip("/")
    resource_path = normalized
    if not normalized.startswith("role_profiles/"):
        resource_path = f"role_profiles/{normalized}"
    data = _load_json_resource(resource_path, label=f"Role {role_item.get('id', '<unknown>')} profile")
    if not isinstance(data, dict):
        raise ValueError(
            f"Bundled profile for role {role_item.get('id', '<unknown>')} must be a JSON object."
        )
    return data


def _validate_weights(role_id: str, weights: Dict[str, float]) -> None:
    """Ensure all weight values are finite, in [0, 1], and not all zero."""
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


def _build_roles(
    data: Dict[str, Any],
    *,
    dimension_ids: List[str],
    source_label: str,
    prompt_profile_loader: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> List[RoleProfile]:
    roles_data = data.get("roles")
    if not isinstance(roles_data, list) or not roles_data:
        raise ValueError(f"{source_label} must define a non-empty 'roles' list.")

    if len(set(dimension_ids)) != len(dimension_ids):
        raise ValueError("Rubric dimension IDs must be unique before loading roles.")

    seen_role_ids: set[str] = set()
    roles: List[RoleProfile] = []
    expected_dims = set(dimension_ids)

    for index, item in enumerate(roles_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{source_label} role #{index} must be a JSON object.")

        role_id = _ensure_non_empty_string(item.get("id"), label=f"role #{index} id")
        if role_id in seen_role_ids:
            raise ValueError(f"{source_label} contains duplicate role id: {role_id}")
        seen_role_ids.add(role_id)

        role_name = _ensure_non_empty_string(item.get("name"), label=f"role '{role_id}' name")
        persona = _ensure_non_empty_string(item.get("persona"), label=f"role '{role_id}' persona")
        weights_raw = item.get("w_prior")
        if not isinstance(weights_raw, dict):
            raise ValueError(f"Role {role_id} must define 'w_prior' as an object.")

        missing = expected_dims - set(weights_raw.keys())
        extra = set(weights_raw.keys()) - expected_dims
        if missing:
            raise ValueError(f"Role {role_id} missing weights for: {sorted(missing)}")
        if extra:
            raise ValueError(f"Role {role_id} has unknown dimensions: {sorted(extra)}")

        try:
            normalized_weights = {dim_id: float(value) for dim_id, value in weights_raw.items()}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Role {role_id} has non-numeric weight values.") from exc
        _validate_weights(role_id, normalized_weights)

        prompt_profile = prompt_profile_loader(item)
        if not isinstance(prompt_profile, dict):
            raise ValueError(f"Role {role_id} prompt profile must be a JSON object.")

        roles.append(
            RoleProfile(
                id=role_id,
                name=role_name,
                persona=persona,
                w_prior=normalized_weights,
                prompt_profile=prompt_profile,
            )
        )

    return roles


def load_roles(path: str | Path, dimension_ids: List[str]) -> List[RoleProfile]:
    """Load role definitions from JSON, validating weights against the rubric."""
    roles_path = Path(path)
    data = _load_json_file(roles_path, label="Roles")
    return _build_roles(
        data,
        dimension_ids=dimension_ids,
        source_label=f"Roles file {roles_path}",
        prompt_profile_loader=lambda item: _load_prompt_profile_from_disk(roles_path, item),
    )


def load_default_roles(dimension_ids: List[str]) -> List[RoleProfile]:
    """Load the bundled default roles and prompt profiles shipped with the package."""
    data = _load_json_resource("roles.json", label="Roles")
    return _build_roles(
        data,
        dimension_ids=dimension_ids,
        source_label="Bundled default roles",
        prompt_profile_loader=_load_prompt_profile_from_package,
    )
