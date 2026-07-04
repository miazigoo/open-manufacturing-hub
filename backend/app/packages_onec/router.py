from fastapi import APIRouter

router = APIRouter(prefix="/api/packages/onec", tags=["packages-onec"])


@router.get("/metadata")
async def metadata():
    return {"package_id": "omh-package-onec", "boundary": "re-export", "status": "active"}
