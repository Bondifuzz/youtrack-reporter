from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging

from .initializer import ArangoDBInitializer
from .interfaces.configs import DBConfigs
from .interfaces.issues import DBIssues
from .interfaces.unsent_mq import DBUnsentMessages
from ..abstract import IDatabase


if TYPE_CHECKING:
    from aioarangodb.database import StandardDatabase
    from aioarangodb.client import ArangoClient
    from youtrack_reporter.app.settings import AppSettings, CollectionSettings
    from ..abstract import IConfigs, IIssues, IUnsentMessages

class ArangoDB():
    _db_configs: IConfigs
    _db_issues: IIssues
    _db_unsent_mq: IUnsentMessages

    _logger: logging.Logger
    _collections: CollectionSettings
    _client: Optional[ArangoClient]
    _db: StandardDatabase

    @property
    def unsent_mq(self):
        return self._db_unsent_mq

    @property
    def configs(self):
        return self._db_configs

    @property
    def issues(self) -> IIssues:
        return self._db_issues

    async def _init(self, settings: AppSettings):

        self._client = None
        self._is_closed = True
        self._logger = logging.getLogger("db")

        db_initializer = await ArangoDBInitializer.create(settings)
        await db_initializer.do_init()

        self._db = db_initializer.db
        self._client = db_initializer.client
        self._collections = db_initializer.collections

        self._db_configs = DBConfigs(self._db, self._collections)
        self._db_issues = DBIssues(self._db, self._collections)
        self._db_unsent_mq = DBUnsentMessages(self._db, self._collections)

    @staticmethod
    async def create(settings):
        _self = ArangoDB()
        await _self._init(settings)
        return _self

    async def close(self):
        
        if self._client is not None:
            await self._client.close()
            self._client = None
        else:
            self._logger.warning(f"Database connection is already closed")

    def __del__(self):
        if self._client is not None:
            self._logger.error("Database connection has not been closed")