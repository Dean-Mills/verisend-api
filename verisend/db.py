from typing import Annotated
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as _AsyncSession

from fastapi import Depends
from forms.settings import settings

connection_str = settings.db_conn_str
if connection_str.startswith("postgresql://"):
       connection_str = connection_str.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    connection_str, 
    pool_size=settings.db_pool_size,
    echo=True
)

async def get_async_session():
    async with _AsyncSession(engine) as session:
        yield session

AsyncSession = Annotated[_AsyncSession, Depends(get_async_session)]