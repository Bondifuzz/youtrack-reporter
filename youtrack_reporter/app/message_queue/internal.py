from typing import TYPE_CHECKING
from pydantic import BaseModel

from mqtransport import MQApp
from mqtransport.participants import Consumer, Producer
from mqtransport.errors import ConsumeMessageError
from youtrack_reporter.app.youtrack import YouTrackError

from youtrack_reporter.app.message_queue.state import MQAppState

if TYPE_CHECKING:
    from youtrack_reporter.app.database.orm import ORMConfig

class MP_VerifyYT(Producer):
    name = "youtrack-reporter.internal.verify"
    class Model(BaseModel):
        config_id: str
        update_rev: str

class MC_VerifyYT(Consumer):
    name = "youtrack-reporter.internal.verify"
    class Model(BaseModel):
        config_id: str
        update_rev: str

    async def consume(self, msg: Model, app: MQApp):
        state: MQAppState = app.state
        config: ORMConfig = await state.db.configs.get(msg.config_id)

        if config is None:
            self._logger.error("Config to verify was not found!")
            raise ConsumeMessageError()
        
        if config.update_rev != msg.update_rev:
            # If it is not last request for validation, return
            return
        
        try:
            # Here we need config = func(config) because we store id 
            # of yt project inside config when validating creds
            config = await state.youtrack_api.validate_credentials(config)
            # Now we have config.project_id
            # And we have to store it in the database
            await state.db.configs.update(config)
            
            await state.producers.youtrack_integration_result.produce(
                config_id=config.id,
                update_rev=config.update_rev,
                error=None
            )
        except YouTrackError as e:
            await state.producers.youtrack_integration_result.produce(
                config_id=config.id,
                update_rev=config.update_rev,
                error=str(e)
            )