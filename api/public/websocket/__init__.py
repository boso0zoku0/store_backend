from fastapi import APIRouter
from .friendly import router as friendly_router_ws
from .helper import router as helper_router_ws
from .notify import router as notification_router_ws

router = APIRouter()
router.include_router(friendly_router_ws)
router.include_router(helper_router_ws)
router.include_router(notification_router_ws)
