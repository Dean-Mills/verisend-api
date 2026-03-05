from fastapi import APIRouter
from . import (
    test
)


TAGS = [
    *test.TAGS,
]

router = APIRouter()
router.include_router(test.router)