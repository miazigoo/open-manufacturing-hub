from __future__ import annotations


class PackageNotInstallableError(Exception):
    def __init__(self, package_id: str, status: str, message: str) -> None:
        self.package_id = package_id
        self.status = status
        self.message = message
        super().__init__(message)
