from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple

from youtrack_reporter.app.database.arangodb.interfaces.base import DBBase
from youtrack_reporter.app.database.errors import DBAlreadyExistsError, DBRecordNotFoundError
from youtrack_reporter.app.database.orm import ORMConfig
from youtrack_reporter.app.database.abstract import IConfigs
from .util import (
    dbkey_to_id,
    id_to_dbkey,
    maybe_already_exists,
    maybe_not_found,
    maybe_unknown_error,
)

if TYPE_CHECKING:
    from aioarangodb.database import StandardDatabase
    from aioarangodb.collection import StandardCollection
    from youtrack_reporter.app.settings import CollectionSettings
    from youtrack_reporter.app.database.arangodb.database import ArangoDB


class DBConfigs(DBBase, IConfigs):

    _col_configs: StandardCollection

    def __init__(
        self,
        db: StandardDatabase,
        collections: CollectionSettings,
    ):
        self._col_configs = db[collections.configs]
        super().__init__(db, collections)

    @maybe_unknown_error
    async def get(self, config_id: str) -> Optional[ORMConfig]:
        doc_dict = await self._col_configs.get(config_id)
        if doc_dict is None:
            raise DBRecordNotFoundError()
        return ORMConfig.parse_obj(dbkey_to_id(doc_dict))

    @maybe_unknown_error
    @maybe_already_exists(DBAlreadyExistsError)
    async def insert(self, config: ORMConfig) -> ORMConfig:
        # doc_dict = id_to_dbkey(config.dict()) # ['id'] -> ['_key'] => '_key' = None
        res = await self._col_configs.insert(config.dict(exclude={'id'}))
        return ORMConfig(**dbkey_to_id({**res, **config.dict()}))

    @maybe_unknown_error
    async def update(self, config: ORMConfig) -> Tuple[ORMConfig, ORMConfig]:
        doc_dict = id_to_dbkey(config.dict())
        res = await self._col_configs.update(
            doc_dict, 
            return_old=True, 
            return_new=True
        )
        # res has format: {"_id":..., "_key":..., ..., "old": {...}, "new": {...}}
        res = dbkey_to_id(res)
        # now res format is {"id": ..., "old": {...}, "new": {...}}

        return (
            ORMConfig(**res['old'], id=res['id']), 
            ORMConfig(**res['new'], id=res['id'])
        )

    @maybe_unknown_error
    @maybe_not_found(DBRecordNotFoundError)
    async def delete(self, config_id: str) -> None:
        await self._col_configs.delete(config_id)

