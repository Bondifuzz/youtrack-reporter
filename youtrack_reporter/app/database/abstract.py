from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from abc import abstractmethod, ABCMeta

if TYPE_CHECKING:
    from youtrack_reporter.app.settings import AppSettings
    from youtrack_reporter.app.database.orm import ORMConfig


class IConfigs(metaclass=ABCMeta):
    @abstractmethod
    async def get(self, config_id: str) -> Optional[ORMConfig]:
        pass

    @abstractmethod
    async def insert(self, config: ORMConfig) -> None:
        pass

    @abstractmethod
    async def update(self, config: ORMConfig) -> Tuple[ORMConfig, ORMConfig]:
        pass

    @abstractmethod
    async def delete(self, config_id: str) -> None:
        pass

class IIssues(metaclass=ABCMeta):
    @abstractmethod
    async def get_issue(self, crash_id: str) -> Optional[str]:
        pass

    @abstractmethod
    async def insert(self, crash_id: str, issue_id: str) -> None:
        pass

class IUnsentMessages(metaclass=ABCMeta):

    """
    Used for saving/loading MQ unsent messages from database.
    """

    @abstractmethod
    async def save_unsent_messages(self, messages: Dict[str, list]):
        pass

    @abstractmethod
    async def load_unsent_messages(self) -> Dict[str, list]:
        pass

class IDatabase(metaclass=ABCMeta):

    """Used for managing database"""

    @classmethod
    @abstractmethod
    async def create(cls, settings: AppSettings):
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @property
    @abstractmethod
    def configs(self) -> IConfigs:
        pass

    @property
    @abstractmethod
    def issues(self) -> IIssues:
        pass

    @property
    @abstractmethod
    def unsent_mq(self) -> IUnsentMessages:
        pass