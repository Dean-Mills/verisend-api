from fastapi import APIRouter
from verisend.api import v1
from . import (
    utils
)

TAGS = [
    *v1.TAGS,
    *utils.TAGS,
]

router = APIRouter()
router.include_router(v1.router, prefix="/v1")
router.include_router(utils.router)

__all__ = ["router", "TAGS"]