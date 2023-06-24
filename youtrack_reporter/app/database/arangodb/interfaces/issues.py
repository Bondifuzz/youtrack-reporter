from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from youtrack_reporter.app.database.arangodb.interfaces.base import DBBase
from youtrack_reporter.app.database.errors import DBAlreadyExistsError, DBRecordNotFoundError
from youtrack_reporter.app.database.abstract import IIssues
from .util import (
    maybe_already_exists,
    maybe_not_found,
    maybe_unknown_error,
)

if TYPE_CHECKING:
    from aioarangodb.database import StandardDatabase
    from aioarangodb.collection import StandardCollection
    from youtrack_reporter.app.settings import CollectionSettings
    from youtrack_reporter.app.database.arangodb.database import ArangoDB


class DBIssues(DBBase, IIssues):

    _col_issues: StandardCollection

    def __init__(
        self,
        db: StandardDatabase,
        collections: CollectionSettings,
    ):
        self._col_issues = db[collections.issues]
        super().__init__(db, collections)

    @maybe_unknown_error
    async def get_issue(self, crash_id: str) -> Optional[str]:
        doc_dict = await self._col_issues.get(crash_id)
        if doc_dict is None:
            raise DBRecordNotFoundError()
        return doc_dict['issue_id']

    @maybe_unknown_error
    @maybe_already_exists(DBAlreadyExistsError)
    async def insert(self, crash_id: str, issue_id: str) -> None:
        doc_dict = {
            "_key": crash_id,
            "issue_id": issue_id
        }
        await self._col_issues.insert(doc_dict)