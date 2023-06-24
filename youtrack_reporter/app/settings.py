from contextlib import suppress
from os import environ
from typing import Optional
from pydantic import AnyHttpUrl, BaseSettings, BaseModel, EmailStr, Field, AnyUrl, root_validator

with suppress(ModuleNotFoundError):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="local/dotenv")

class EnvironmentSettings(BaseSettings):
    shutdown_timeout: int = Field(env="SHUTDOWN_TIMEOUT")

class ServerSettings(BaseSettings):

    host: str
    port: str

    class Config:
        env_prefix = "SERVER_"

class ShutdownSettings(BaseSettings):
    timeout: int
    class Config:
        env_prefix = "SHUTDOWN_"

class DatabaseSettings(BaseSettings):
    engine: str = Field(regex=r"^arangodb$")
    url: AnyHttpUrl
    username: str
    password: str
    name: str

    class Config:
        env_prefix = "DB_"

class MessageQueues(BaseSettings):
    youtrack_reporter_internal: str
    youtrack_reporter: str
    api_gateway: str
    dlq: str

    class Config:
        env_prefix = "MQ_QUEUE_"

class MessageQueueSettings(BaseSettings):

    url: Optional[AnyUrl]
    broker: str = Field(regex="^sqs$")
    queues: MessageQueues
    username: str
    password: str
    region: str

    class Config:
        env_prefix = "MQ_"

class CollectionSettings(BaseSettings):
    configs: str = "Configs"
    issues: str = "Issues"
    unsent_messages: str = "UnsentMessages"

class AppSettings(BaseModel):
    server: ServerSettings
    database: DatabaseSettings
    collections: CollectionSettings
    message_queue: MessageQueueSettings
    environment: EnvironmentSettings

def load_app_settings():
    return AppSettings(
        server=ServerSettings(),
        database=DatabaseSettings(),
        collections=CollectionSettings(),
        message_queue=MessageQueueSettings(queues=MessageQueues()),
        environment=EnvironmentSettings()
    )