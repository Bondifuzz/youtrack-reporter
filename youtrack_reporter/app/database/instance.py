from __future__ import annotations
from typing import TYPE_CHECKING

from .arangodb.database import ArangoDB
import logging

if TYPE_CHECKING:
    from ..settings import AppSettings
    from .abstract import IDatabase


async def db_init(settings: AppSettings) -> IDatabase:

    logger = logging.getLogger("db")
    db_engine = settings.database.engine.lower()

    if db_engine == "arangodb":
        logger.info("Using ArangoDB driver")
        db = await ArangoDB.create(settings)
    else:
        raise ValueError(f"Invalid database engine '{db_engine}'")

    return db
