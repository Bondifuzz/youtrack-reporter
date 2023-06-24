from __future__ import annotations
from typing import TYPE_CHECKING
from unittest import result
from aiohttp import web
from mqtransport.src.base.app import MQApp

from youtrack_reporter.app.youtrack import YouTrackAsyncAPI
from youtrack_reporter.app.database.instance import db_init
from youtrack_reporter.app.message_queue.instance import mq_init
from youtrack_reporter.app.message_queue.state import MQAppState
from youtrack_reporter.app.database.errors import DBRecordNotFoundError
from youtrack_reporter.app.database.orm import ORMConfig

import logging

if TYPE_CHECKING:
    from youtrack_reporter.app.message_queue.state import MQAppState
    from mqtransport import MQApp
    from youtrack_reporter.app.settings import AppSettings

def configure_web_server():

    logger = logging.getLogger("Server")
    logger.info(f"Configuring web server...")

    with open("index.html") as f:
        index_html = f.read()

    routes = web.RouteTableDef()

    @routes.get("/")
    async def index(request: web.Request):
        return web.Response(
            text=index_html,
            content_type="text/html",
            charset="utf-8",
        )
    
    @routes.get("/metrics")
    async def metrics(request: web.Request):
        return web.Response(
            body="should be some metrics, i don't know exactly",
            content_type="text/plain; version=0.0.4;",
        )
    
    @routes.get("/docs")
    async def docs(request: web.Request):
        return web.Response(
            body="Documentation!!!",
            content_type="text/plain; version=0.0.4;",
        )

    @routes.get(r"/api/v1/integrations/{id}")
    async def get_config(request: web.Request):
        req_id = request.match_info["id"]
        state: MQAppState = request.app['mq'].state
        
        config: ORMConfig = await state.db.configs.get(req_id)
        if config:
            code = 200
            error = None
            result = config.dict(exclude={'project_id'})
        else:
            code = 404
            error = "Not found"
            result = dict()
        

        status = "OK" if error is None else "Failed"
        return web.json_response(
            status=code,
            data=dict(
                status=status,
                error=error,
                result=result,
            ),
        )

    @routes.post(r"/api/v1/integrations")
    async def insert_config(request: web.Request):
        state: MQAppState = request.app['mq'].state

        if request.can_read_body:
            body = await request.json()
            config: ORMConfig = ORMConfig(**body)
            config.id = None

            config = await state.db.configs.insert(config)
            if config.id is None:
                raise
            
            await state.producers.verify_youtrack.produce(
                config_id=config.id,
                update_rev=config.update_rev,
            )

            code = 202
            error = None
            result = dict(
                id=config.id
            )
        else:
            code = 422
            status = "Request body must be provided"
            result = dict()
        
        status = "OK" if error is None else "Failed"
        return web.json_response(
            status=code,
            data=dict(
                status=status,
                error=error,
                result=result,
            )
        )

    @routes.put(r"/api/v1/integrations/{id}")
    async def update_config(request: web.Request):
        config_id = request.match_info['id']
        state: MQAppState = request.app['mq'].state

        result = dict()

        if request.can_read_body:
            body = await request.json()
            config: ORMConfig = ORMConfig(**body)
            config.id = config_id
            try:
                (old_config, new_config) = await state.db.configs.update(config)

                result['old'] = old_config.dict(exclude={'id', 'update_rev', 'project_id'})
                result['new'] = new_config.dict(exclude={'id', 'update_rev', 'project_id'})

                await state.producers.verify_youtrack.produce(
                    config_id=config.id,
                    update_rev=config.update_rev,
                )

                code = 202
                error = None
            except DBRecordNotFoundError:
                code = 404
                error = "Record not found"
        else:
            code = 422
            error = "Request body must be provided"
        
        status = "OK" if error is None else "Failed"
        return web.json_response(
            status=code,
            data=dict(
                status=status,
                error=error,
                result=result,
            )
        )

    @routes.delete(r"/api/v1/integrations/{id}")
    async def delete_config(request: web.Request):
        config_id = request.match_info['id']
        state: MQAppState = request.app['mq'].state

        try:
            await state.db.configs.delete(config_id)
            code = 204
            error = None
        except DBRecordNotFoundError:
            code = 404
            error = "Record not found"
        
        status = "OK" if error is None else "Failed"
        return web.json_response(
            status=code,
            data=dict(
                status=status,
                error=error,
                result=dict(),
            )
        )

    @web.middleware
    async def unhandled_exception_middleware(request: web.Request, handler):
        try:
            return await handler(request)
        #except web.HTTPException: # HTTPNotFound
        #    raise
        except DBRecordNotFoundError as e:
            logger.error(f"Database record not found!")
            return web.json_response(
                status=404,
                data=dict(
                    status="Failed",
                    error="Database record not found",
                    result = dict()
                )
            )
        except:
            if request.path.startswith("/api/"):
                logger.exception("Error handling request")
                return web.json_response(
                    status=500,
                    data=dict(
                        status="Failed",
                        error="Internal error",
                        result=dict(),
                    )
                )
            else:
                raise

    app = web.Application()
    # setup_openapi(app, "local/openapi.json", routes)
    app.add_routes(routes)
    app.middlewares.append(unhandled_exception_middleware)

    logger.info(f"Server configuration done")

    return app

def run(settings: AppSettings):
    app = configure_web_server()
    logger = logging.getLogger("main")

    async def server_init(app: web.Application):
        logger.info("Configuring message queue...")
        mq_app: MQApp = await mq_init(settings)
        logger.info("Configuring message queue... OK")

        state: MQAppState = mq_app.state
        state.settings = settings

        logger.info("Configuring database...")
        state.db = await db_init(settings)
        logger.info("Configuring database... OK")

        logger.info("Loading MQ unsent messages...")
        messages = await state.db.unsent_mq.load_unsent_messages()
        mq_app.import_unsent_messages(messages)
        logger.info("Loading MQ unsent messages... OK")

        state.youtrack_api = YouTrackAsyncAPI()

        await mq_app.start()
        app['mq'] = mq_app

    async def server_exit(app):
        mq_app: MQApp = app["mq"]
        state: MQAppState = mq_app.state

        logger.info("Closing message queue...")
        timeout = settings.environment.shutdown_timeout
        await mq_app.shutdown(timeout)
        logger.info("Closing message queue... OK")

        logger.info("Saving MQ unsent messages...")
        messages = mq_app.export_unsent_messages()
        await state.db.unsent_mq.save_unsent_messages(messages)
        logger.info("Saving MQ unsent messages... OK")

        logger.info("Closing database...")
        await state.db.close()
        logger.info("Closing database... OK")

        logger.info("Closing aiohttp client...")
        await state.youtrack_api.__aexit__()
        logger.info("Closing aiohttp client... OK")

    host = settings.server.host
    port = settings.server.port

    app.on_startup.append(server_init)
    app.on_shutdown.append(server_exit)

    web.run_app(app, host=host, port=port, access_log=None)