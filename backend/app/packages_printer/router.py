from fastapi import APIRouter

router = APIRouter(prefix="/api/packages/printer", tags=["packages-printer"])


@router.get("/metadata")
async def metadata():
    return {"package_id": "omh-package-printer", "boundary": "re-export", "status": "active"}
