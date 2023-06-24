from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aioarangodb.database import StandardDatabase
    from youtrack_reporter.app.settings import CollectionSettings
    from youtrack_reporter.app.database.arangodb.database import ArangoDB


class DBBase:

    _db: StandardDatabase
    _collections: CollectionSettings

    def __init__(self, db: StandardDatabase, collections: CollectionSettings):
        self._collections = collections
        self._db = db