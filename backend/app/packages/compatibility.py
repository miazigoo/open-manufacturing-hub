from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from app.packages.manifest import PackageManifest

DEFAULT_CORE_VERSION = "0.1.0"


def core_version() -> str:
    try:
        return version("open-manufacturing-hub-backend")
    except PackageNotFoundError:
        return DEFAULT_CORE_VERSION


def validate_compatibility(manifest: PackageManifest, current_version: str | None = None) -> list[str]:
    current = current_version or core_version()
    errors: list[str] = []
    if _compare_versions(current, manifest.core_version_min) < 0:
        errors.append(f"Core {current} is lower than required {manifest.core_version_min}")
    if manifest.core_version_max and not _matches_max(current, manifest.core_version_max):
        errors.append(f"Core {current} is outside supported range <= {manifest.core_version_max}")
    return errors


def is_compatible(manifest: PackageManifest, current_version: str | None = None) -> bool:
    return not validate_compatibility(manifest, current_version)


def _matches_max(current: str, maximum: str) -> bool:
    if maximum.endswith(".x"):
        parts = _parts(maximum[:-2])
        if len(parts) == 1:
            upper = [parts[0] + 1, 0, 0]
        else:
            upper = [parts[0], parts[1] + 1, 0]
        return _compare_version_parts(_parts(current), upper) < 0
    return _compare_versions(current, maximum) <= 0


def _compare_versions(left: str, right: str) -> int:
    return _compare_version_parts(_parts(left), _parts(right))


def _compare_version_parts(left_parts: list[int], right_parts: list[int]) -> int:
    size = max(len(left_parts), len(right_parts))
    left_parts += [0] * (size - len(left_parts))
    right_parts += [0] * (size - len(right_parts))
    return (left_parts > right_parts) - (left_parts < right_parts)


def _parts(value: str) -> list[int]:
    clean = value.replace("-", ".").split(".")
    parts: list[int] = []
    for item in clean:
        if item == "x":
            break
        number = "".join(char for char in item if char.isdigit())
        parts.append(int(number or 0))
    return parts or [0]
