from aioarangodb.database import StandardDatabase
from aioarangodb import ArangoClient

from youtrack_reporter.app.settings import AppSettings, CollectionSettings

from ..errors import DatabaseError
import logging

########################################
# ArangoDB Base Initializer
########################################


class ArangoDBBaseInitializer:

    _client: ArangoClient
    _db: StandardDatabase
    _logger: logging.Logger

    # @staticmethod
    # def get_logger(self):
    #     return logging.getLogger("db.init")
    
    def __init__(self) -> None:
        self._logger = logging.getLogger("db.init")

    async def _init(self, settings: AppSettings):
        
        db_name = settings.database.name
        username = settings.database.username
        password = settings.database.password

        self._client = ArangoClient(settings.database.url)
        self._db = await self._client.db(db_name, username, password)

    async def _verify_auth(self):

        self._logger.info("Signing in as user '%s'", self._db.username)
        self._logger.info("Using database '%s'", self._db.name)

        try:
            await self._db.conn.ping()
        except Exception as e:
            msg = f"Failed to open database '{self._db.name}'. Reason - {e}"
            raise DatabaseError(msg) from e
    
    async def _check_user_permissions(self):
        
        permissions = await self._db.permission(self._db.username, self._db.name)

        if permissions != "rw":
            msg = f"Not enough permissions to administrate database: '{permissions}'"
            raise DatabaseError(msg)

    def get_init_tasks(self):
        yield "Authentication", self._verify_auth()
        yield "Check permissions", self._check_user_permissions()

    @staticmethod
    async def create(settings):
        self = ArangoDBBaseInitializer()
        await self._init(settings)
        return self

    async def _create_collections(self, collections):

        batch_db = self._db.begin_batch_execution(return_result=False)
        existent_cols = [col["name"] for col in await self._db.collections()]

        for collection in collections:
            col_name = collection["name"]
            if col_name not in existent_cols:
                self._logger.info("Collection '%s' does not exist. Creating...", col_name)
                await batch_db.create_collection(**collection)
            else:
                self._logger.info("Collection '%s' already exists", col_name)

        await batch_db.commit()

    async def do_init(self):

        try:
            self._logger.info("Initializing database...")

            for name, task in self.get_init_tasks():
                self._logger.info("Performing '%s'", name)
                await task

            self._logger.info("Initializing database... OK")

        except:
            await self._client.close()
            raise

    @property
    def db(self):
        return self._db

    @property
    def client(self):
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None

########################################
# ArangoDB Initializer
########################################


class ArangoDBInitializer(ArangoDBBaseInitializer):
    _collections: CollectionSettings

    async def _init(self, settings: AppSettings):
        await super()._init(settings)
        self._collections = settings.collections

    async def _create_all_collections(self):
        await self._create_collections(
            [
                {"name": self._collections.configs},
                {"name": self._collections.issues},
                {"name": self._collections.unsent_messages},
            ]
        )

    def get_init_tasks(self):
        yield from super().get_init_tasks()
        yield "Create collections", self._create_all_collections()

    @staticmethod
    async def create(settings):
        self = ArangoDBInitializer()
        await self._init(settings)
        return self

    async def do_init(self):

        try:
            self._logger.info("Initializing database with collections...")
            for name, task in self.get_init_tasks():
                self._logger.info("Performing '%s'", name)
                await task

            self._logger.info("Initializing database... OK")

        except:
            await self._client.close()
            raise

    @property
    def collections(self):
        return self._collections