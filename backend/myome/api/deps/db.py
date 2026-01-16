"""Database dependencies"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from myome.core.database import get_session

# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_session)]
