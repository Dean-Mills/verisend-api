from fastapi import APIRouter
from . import (
    test,
    setups,
    standard_fields,
)


TAGS = [
    *test.TAGS,
    *setups.TAGS,
    *standard_fields.TAGS,
]

router = APIRouter()
router.include_router(test.router)
router.include_router(setups.router)
router.include_router(standard_fields.router)