"""I8 purity lock: resolve_place_geography must not import forbidden seams.

Forbidden: FortyGuard, q_A, Decision 8, demo allowance, reference observations.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.unit.test_national_resolver_integration import (
    _find_impl,
    load_resolve_place_geography,
    load_selection_module,
)

FORBIDDEN_IMPORT_FRAGMENTS = (
    "fortyguard",
    "demo_allowance",
    "demo_acquisition",
    "demo_policy_config",
    "hazard_spread",
    "phoenix_v1_reference",
    "phoenix_v1_thermal",
    "decision8",
    "decision_8",
)

FORBIDDEN_SOURCE_IMPORT_LINES = (
    "from app.integrations.fortyguard",
    "import fortyguard",
    "from app.domain.demo_allowance",
    "from app.services.demo_allowance",
    "from app.services.demo_acquisition",
    "from app.services.phoenix_v1_reference",
    "from app.services.hazard_spread",
)

REFERENCE_OBSERVATION_MARKERS = (
    "observations.jsonl",
    "resolve_ready_area_package",
    "load_phoenix_v1_reference_panel",
)


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _assert_module_is_pure(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    imported = _imported_modules(source)
    for name in imported:
        lowered = name.lower().replace("-", "_")
        for fragment in FORBIDDEN_IMPORT_FRAGMENTS:
            assert fragment not in lowered, f"{path.name} imports {name!r}"
        assert "q_a" not in lowered.split(".")[-1].lower()
    for line in FORBIDDEN_SOURCE_IMPORT_LINES:
        assert line not in source, f"{path.name} contains {line!r}"
    for marker in REFERENCE_OBSERVATION_MARKERS:
        assert marker not in source, f"{path.name} references {marker!r}"


def _resolve_place_geography_files() -> list[Path]:
    files: list[Path] = []
    named = _find_impl("app", "services", "resolve_place_geography.py")
    if named is not None:
        files.append(named)
    impl = _find_impl("app", "services", "place_geography_resolver.py")
    if impl is not None:
        files.append(impl)
    extras = (
        ("app", "services", "national_resolver.py"),
        ("app", "services", "national_place_geography.py"),
        ("app", "domain", "resolve_place_geography.py"),
    )
    for rel in extras:
        found = _find_impl(*rel)
        if found is not None:
            files.append(found)
    selection = _find_impl("app", "services", "national_tract_selection.py")
    if selection is not None:
        text = selection.read_text(encoding="utf-8")
        if "def resolve_place_geography" in text:
            files.append(selection)
    return files


def test_resolve_place_geography_module_does_not_import_forbidden_seams() -> None:
    files = _resolve_place_geography_files()
    if not files and load_resolve_place_geography() is None:
        pytest.skip(
            "resolve_place_geography module not on this worktree (Lead stitch pending)"
        )
    if not files:
        pytest.skip(
            "resolve_place_geography is imported but has no inspectable source "
            "(Lead stitch pending)"
        )
    for path in files:
        _assert_module_is_pure(path)


def test_selector_and_package_modules_stay_vendor_and_reference_free() -> None:
    paths = [
        _find_impl("app", "services", "national_tract_selection.py"),
        _find_impl("app", "domain", "national_geography_package.py"),
        _find_impl("app", "services", "national_geography_materializer.py"),
    ]
    present = [path for path in paths if path is not None]
    if not present:
        pytest.skip(
            "national resolver modules not on this worktree (Lead stitch pending)"
        )
    for path in present:
        _assert_module_is_pure(path)


def test_selection_module_object_has_no_forbidden_imports() -> None:
    module = load_selection_module()
    if module is None:
        pytest.skip(
            "national tract selector not on this worktree (Lead stitch pending)"
        )
    path = Path(module.__file__ or "")
    assert path.is_file()
    _assert_module_is_pure(path)
