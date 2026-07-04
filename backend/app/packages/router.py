from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.packages import service
from app.packages.schemas import InstalledPackageRead, PackageActionResponse, PackageAvailableRead, PackageCapabilityRead, PackageCompatibilityReport, PackageDocsRead, PackageExportRead, PackageInstallRequest, PackageNavigationRead, PackageRouteInventoryItem, PackageUpgradeRead

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("/available", response_model=list[PackageAvailableRead])
async def available_packages(session: AsyncSession = Depends(get_session)):
    return await service.available_packages(session)


@router.get("/installed", response_model=list[InstalledPackageRead])
async def installed_packages(session: AsyncSession = Depends(get_session)):
    return await service.installed_packages(session)


@router.get("/navigation", response_model=list[PackageNavigationRead])
async def package_navigation(session: AsyncSession = Depends(get_session)):
    return await service.package_navigation(session)


@router.get("/export-config", response_model=PackageExportRead)
async def export_config(session: AsyncSession = Depends(get_session)):
    return await service.export_config(session)


@router.get("/capabilities", response_model=list[PackageCapabilityRead])
async def package_capabilities(session: AsyncSession = Depends(get_session)):
    return await service.package_capabilities(session)


@router.get("/compatibility-report", response_model=PackageCompatibilityReport)
async def compatibility_report(session: AsyncSession = Depends(get_session)):
    return await service.compatibility_report(session)


@router.get("/route-inventory", response_model=list[PackageRouteInventoryItem])
async def route_inventory(request: Request):
    return service.route_inventory(list(request.app.routes))


@router.get("/{package_id}", response_model=PackageAvailableRead)
async def package_details(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.package_details(session, package_id)


@router.post("/{package_id}/install", response_model=PackageActionResponse)
async def install_package(package_id: str, payload: PackageInstallRequest | None = None, http_request: Request = None, session: AsyncSession = Depends(get_session)):
    package, log = await service.install_package(session, package_id, install_demo_data=bool(payload and payload.install_demo_data))
    await audit_service.record_change(session, request=http_request, action="package.installed", category="packages", object_type="package", object_id=package.package_id, object_name=package.name, before=None, after=audit_service.snapshot_model(package), summary=f"Package {package.package_id} installed", details={"install_demo_data": bool(payload and payload.install_demo_data), "log": log}, package_id=package.package_id)
    await session.commit()
    return {"package": package, "log": log}


@router.post("/{package_id}/enable", response_model=InstalledPackageRead)
async def enable_package(package_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    before_package = await service.package_details(session, package_id)
    package = await service.enable_package(session, package_id)
    await audit_service.record_change(session, request=http_request, action="package.enabled", category="packages", object_type="package", object_id=package.package_id, object_name=package.name, before=before_package, after=audit_service.snapshot_model(package), summary=f"Package {package.package_id} enabled", package_id=package.package_id)
    await session.commit()
    return package


@router.post("/{package_id}/disable", response_model=InstalledPackageRead)
async def disable_package(package_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    before_package = await service.package_details(session, package_id)
    package = await service.disable_package(session, package_id)
    await audit_service.record_change(session, request=http_request, action="package.disabled", category="packages", object_type="package", object_id=package.package_id, object_name=package.name, before=before_package, after=audit_service.snapshot_model(package), summary=f"Package {package.package_id} disabled", package_id=package.package_id)
    await session.commit()
    return package


@router.post("/{package_id}/uninstall", status_code=204)
async def uninstall_package(package_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    before_package = await service.package_details(session, package_id)
    await service.uninstall_package(session, package_id)
    await audit_service.record_change(session, request=http_request, action="package.uninstalled", category="packages", object_type="package", object_id=package_id, object_name=package_id, before=before_package, after=None, summary=f"Package {package_id} uninstalled", package_id=package_id)
    await session.commit()
    return Response(status_code=204)


@router.post("/{package_id}/install-demo-data")
async def install_demo_data(package_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    log = await service.install_demo_data(session, package_id)
    await audit_service.record_action(session, request=http_request, action="package.demo_data_installed", category="packages", object_type="package", object_id=package_id, object_name=package_id, summary=f"Demo data installed for package {package_id}", details={"log": log}, package_id=package_id)
    await session.commit()
    return {"package_id": package_id, "log": log}


@router.get("/{package_id}/docs", response_model=PackageDocsRead)
async def package_docs(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.package_docs(session, package_id)


@router.get("/{package_id}/capabilities", response_model=list[PackageCapabilityRead])
async def package_capabilities_by_id(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.package_capabilities(session, package_id)


@router.get("/{package_id}/check-upgrade", response_model=PackageUpgradeRead)
async def check_upgrade(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.check_upgrade(session, package_id)


@router.post("/{package_id}/mark-upgraded", response_model=PackageUpgradeRead)
async def mark_upgraded(package_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.mark_upgraded(session, package_id)
    await audit_service.record_action(session, request=http_request, action="package.mark_upgraded", category="packages", object_type="package", object_id=package_id, object_name=package_id, summary=f"Package {package_id} marked upgraded", details=result, package_id=package_id)
    await session.commit()
    return result
