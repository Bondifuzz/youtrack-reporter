from youtrack_reporter.app.settings import load_app_settings
from youtrack_reporter.app.message_queue.state import MQAppState
from youtrack_reporter.app.database.instance import db_init
from youtrack_reporter.app.youtrack import YouTrackAsyncAPI

from youtrack_reporter.app.youtrack import YouTrackAsyncAPI
from youtrack_reporter.app.database.instance import db_init
from youtrack_reporter.app.message_queue.state import MQAppState

#Remove, only for testing
from youtrack_reporter.app.database.orm import ORMConfig
from youtrack_reporter.app.database.errors import DatabaseError
import logging

import asyncio
import logging
import coloredlogs

import configparser

async def main():
    fmt = "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
    logging.basicConfig(format=fmt, level=logging.DEBUG)
    logger = logging.getLogger("main")
    coloredlogs.install(level='DEBUG', logger=logger)

    settings = load_app_settings()

    state: MQAppState = MQAppState()
    state.settings = settings
    logger.info("Configuring database...")
    state.db = await db_init(settings)
    logger.info("Configuring database... OK")    
    
    state.youtrack_api = YouTrackAsyncAPI()

    data = configparser.ConfigParser()
    data.read('local/example.ini')
    keys = [i for i in data['CONFIG']]
    vals = [data['CONFIG'][i] for i in data['CONFIG']]

    conf = ORMConfig(**(dict(zip(keys, vals))))

    
    try:
        conf = await state.db.configs.insert(conf)
    except DatabaseError as e:
        logger.warning(f"This config already exists!")

    try:
        conf = await state.db.configs.get("0")
    except DatabaseError as e:
        logger.warning(f"Config with id 0 not found")

    try:
        prev, new = await state.db.configs.update(conf)
        logger.debug(f"prev = {prev.dict()}")
        logger.debug(f"new = {new.dict()}")
    except DatabaseError as e:
        logger.warning(f"update failed!")

    try:
        conf = await state.db.configs.get("0")
        logger.debug(f"conf = {conf.dict()}")
    except DatabaseError as e:
        logger.warning(f"This config already exists!")
    
    try:
        await state.db.issues.insert("1", "0-0")
    except DatabaseError as e:
        logger.warning(f"This issue already exists!")

    logger.info("Closing database...")
    await state.db.close()
    logger.info("Closing database... OK")

    logger.info("Closing aiohttp client...")
    await state.youtrack_api.__aexit__()
    logger.info("Closing aiohttp client... OK")



    
asyncio.run(main())