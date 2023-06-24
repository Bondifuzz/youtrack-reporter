from __future__ import annotations
from typing import TYPE_CHECKING

from mqtransport import SQSApp

# import api_gateway message consumers
from youtrack_reporter.app.message_queue.api_gateway import MC_DuplicateCrashFound, MC_UniqueCrashFound
# import api_gateway message producers
from youtrack_reporter.app.message_queue.api_gateway import MP_YTReportUndelivered, MP_YTIntegrationResult

from youtrack_reporter.app.message_queue.internal import MP_VerifyYT, MC_VerifyYT
from youtrack_reporter.app.message_queue.state import MQAppState

if TYPE_CHECKING:
    from youtrack_reporter.app.settings import AppSettings
    from mqtransport import MQApp
    from mqtransport.channel import ConsumingChannel, ProducingChannel


class Producers:
    youtrack_report_undelivered: MP_YTReportUndelivered
    youtrack_integration_result: MP_YTIntegrationResult

    verify_youtrack: MP_VerifyYT


class MQAppInitializer:

    _settings: AppSettings
    _app: MQApp
    _in_channel: ConsumingChannel
    _ich_internal: ConsumingChannel
    _och_internal: ProducingChannel
    _och_api_gateway: ProducingChannel

    @property
    def app(self):
        return self._app

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._app = None

    async def do_init(self):

        self._app = await self._create_mq_app()
        self._app.state = MQAppState()

        try:
            await self._app.ping()
            await self._configure_channels()

        except:
            await self._app.shutdown()
            raise

    async def _create_mq_app(self):

        broker = self._settings.message_queue.broker.lower()
        settings = self._settings.message_queue

        if broker == "sqs":
            return await SQSApp.create(
                settings.username,
                settings.password,
                settings.region,
                settings.url,
            )

        raise ValueError(f"Unsupported message broker: {broker}")

    async def _create_own_channel(self):
        queues = self._settings.message_queue.queues
        ich = await self._app.create_consuming_channel(queues.youtrack_reporter)
        dlq = await self._app.create_producing_channel(queues.dlq)
        ich.use_dead_letter_queue(dlq)
        self._in_channel = ich

    async def _create_other_channels(self):
        queues = self._settings.message_queue.queues
        self._och_api_gateway = await self._app.create_producing_channel(queues.api_gateway)

        self._ich_internal = await self._app.create_consuming_channel(queues.youtrack_reporter_internal)
        self._och_internal = await self._app.create_producing_channel(queues.youtrack_reporter_internal)

    def _setup_internal_communication(self, producers: Producers):

        ich = self._ich_internal
        och = self._och_internal

        # Incoming messages
        ich.add_consumer(MC_VerifyYT())

        # Outcoming messages
        producers.verify_youtrack = MP_VerifyYT()
        och.add_producer(producers.verify_youtrack)

    def _setup_api_gateway_communication(self, producers: Producers):

        ich = self._in_channel
        och = self._och_api_gateway

        # Incoming messages
        ich.add_consumer(MC_UniqueCrashFound())
        ich.add_consumer(MC_DuplicateCrashFound())

        # Outcoming messages
        producers.youtrack_report_undelivered = MP_YTReportUndelivered()
        producers.youtrack_integration_result = MP_YTIntegrationResult()

        och.add_producer(producers.youtrack_report_undelivered)
        och.add_producer(producers.youtrack_integration_result)

    async def _configure_channels(self):
        await self._create_own_channel()
        await self._create_other_channels()

        state: MQAppState = self.app.state
        state.producers = Producers()

        self._setup_api_gateway_communication(state.producers)
        self._setup_internal_communication(state.producers)


async def mq_init(settings: AppSettings):
    initializer = MQAppInitializer(settings)
    await initializer.do_init()
    return initializer.app