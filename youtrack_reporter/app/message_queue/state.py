from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..youtrack import YouTrackAsyncAPI
    from youtrack_reporter.app.settings import AppSettings
    from youtrack_reporter.app.database.abstract import IDatabase
    from youtrack_reporter.app.message_queue.instance import Producers



class MQAppState:
    youtrack_api: YouTrackAsyncAPI
    db: IDatabase
    settings: AppSettings
    producers: Producers