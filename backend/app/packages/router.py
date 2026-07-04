from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.packages import service
from app.packages.schemas import InstalledPackageRead, PackageActionResponse, PackageAvailableRead, PackageDocsRead, PackageExportRead, PackageInstallRequest, PackageNavigationRead

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


@router.get("/{package_id}", response_model=PackageAvailableRead)
async def package_details(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.package_details(session, package_id)


@router.post("/{package_id}/install", response_model=PackageActionResponse)
async def install_package(package_id: str, request: PackageInstallRequest | None = None, session: AsyncSession = Depends(get_session)):
    package, log = await service.install_package(session, package_id, install_demo_data=bool(request and request.install_demo_data))
    await session.commit()
    return {"package": package, "log": log}


@router.post("/{package_id}/enable", response_model=InstalledPackageRead)
async def enable_package(package_id: str, session: AsyncSession = Depends(get_session)):
    package = await service.enable_package(session, package_id)
    await session.commit()
    return package


@router.post("/{package_id}/disable", response_model=InstalledPackageRead)
async def disable_package(package_id: str, session: AsyncSession = Depends(get_session)):
    package = await service.disable_package(session, package_id)
    await session.commit()
    return package


@router.post("/{package_id}/uninstall", status_code=204)
async def uninstall_package(package_id: str, session: AsyncSession = Depends(get_session)):
    await service.uninstall_package(session, package_id)
    await session.commit()
    return Response(status_code=204)


@router.post("/{package_id}/install-demo-data")
async def install_demo_data(package_id: str, session: AsyncSession = Depends(get_session)):
    log = await service.install_demo_data(session, package_id)
    await session.commit()
    return {"package_id": package_id, "log": log}


@router.get("/{package_id}/docs", response_model=PackageDocsRead)
async def package_docs(package_id: str, session: AsyncSession = Depends(get_session)):
    return await service.package_docs(session, package_id)
