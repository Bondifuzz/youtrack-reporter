from __future__ import annotations
from contextlib import suppress
import string
from pydantic import AnyHttpUrl, BaseModel
from random import randint
import logging
import asyncio

from mqtransport import MQApp, SQSApp
from mqtransport.participants import Producer
from settings import AppSettings, load_app_settings

import random
import sys

config_id: str = None

class MP_UniqueCrashFound(Producer):

    name: str = "youtrack-reporter.crashes.unique"

    class Model(BaseModel):

        config_id: str
        """ Unique config id used to find integration """

        crash_id: str
        """ Unique id of crash """

        crash_info: str
        """ Short description for crash """

        crash_type: str
        """ Type of crash: crash, oom, timeout, leak, etc.. """

        crash_output: str
        """ Crash output (long multiline text) """

        crash_url: AnyHttpUrl
        """ URL can be opened to read crash information """

        project_name: str
        """ Name of project. Used for grouping YT issues """

        fuzzer_name: str
        """ Name of fuzzer. Used for grouping YT issues """

        revision_name: str
        """ Name of fuzzer revision. Used for grouping YT issues """

class MP_DuplicateCrashFound(Producer):

    """Send notification to youtrack that duplicate of crash is found"""

    name: str = "youtrack-reporter.crashes.duplicate"

    class Model(BaseModel):

        config_id: str
        """ Unique config id used to find integration """

        crash_id: str
        """ Unique id of crash """

        duplicate_count: int
        """ Count of similar crashes found (at least) """



class MQAppState:
    mp_ucf: MP_UniqueCrashFound
    mp_dcf: MP_DuplicateCrashFound


class MQAppProduceInitializer:

    _settings: AppSettings
    _app: MQApp

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
            app = await SQSApp.create(
                settings.username,
                settings.password,
                settings.region,
                settings.url,
            )
        else:
            raise ValueError(f"Unsupported message broker: {broker}")

        return app

    async def _configure_channels(self):

        state: MQAppState = self._app.state
        queues = self._settings.message_queue.queues
        channel = await self._app.create_producing_channel(queues.basic)

        mp_ucf = MP_UniqueCrashFound()
        channel.add_producer(mp_ucf)
        state.mp_ucf = mp_ucf

        mp_dcf = MP_DuplicateCrashFound()
        channel.add_producer(mp_dcf)
        state.mp_dcf = mp_dcf


async def create_mq_instance():
    settings = load_app_settings()
    initializer = MQAppProduceInitializer(settings)
    await initializer.do_init()
    return initializer.app


async def producing_loop(mq_app: MQApp):

    state: MQAppState = mq_app.state
    ucf = state.mp_ucf
    dcf = state.mp_dcf

    crash_id = random.randint(1, 100000)

    info = {"config_id": f"{config_id}",
        "crash_id": f"{crash_id}",
        "crash_info": "".join(random.choices(string.ascii_letters, k=35)),
        "crash_type": "".join(random.choices(string.ascii_letters, k=6)),
        "crash_output": "".join(random.choices(string.ascii_letters, k=355)),
        "crash_url": "https://example.com",
        "project_name": " Name of project. Used for grouping YT issues ",
        "fuzzer_name": " Name of fuzzer. Used for grouping YT issues ",
        "revision_name": " Name of fuzzer revision. Used for grouping YT issues "}

    await ucf.produce(**info)
    ucf.logger.info(f"Producing: {info}")

    dinfo = {
        "config_id": f"{config_id}",
        "crash_id": f"{crash_id}",
        "duplicate_count": f"{random.randint(0, 100)}"
    }
    await dcf.produce(**dinfo)
    dcf.logger.info(f"Producting: {dinfo}")


if __name__ == "__main__":

    if(len(sys.argv) != 2):
        print("Please specify config id")
        exit()
    
    config_id = sys.argv[1]

    #
    # Setup logging. Make some loggers silent to avoid mess
    #

    fmt = "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
    logging.basicConfig(format=fmt, level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    #
    # Start application
    # We need loop to start app coroutine
    #

    loop = asyncio.get_event_loop()
    logging.info("Creating MQApp")
    mq_app = loop.run_until_complete(create_mq_instance())

    try:
        logging.info("Running MQApp. Press Ctrl+C to exit")
        loop.run_until_complete(mq_app.start())
        loop.run_until_complete(producing_loop(mq_app))

    except KeyboardInterrupt as e:
        logging.warning("KeyboardInterrupt received")

    finally:
        logging.info("Shutting MQApp down")
        loop.run_until_complete(mq_app.shutdown())
