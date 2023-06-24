from youtrack_reporter.app.youtrack import YouTrackAsyncAPI, YTIssue
from youtrack_reporter.app.errors import YouTrackError
from youtrack_reporter.app.database.orm import ORMConfig

import asyncio

import logging
import coloredlogs
from logging.config import dictConfig
import configparser
import yaml

async def main():
    with open("logging.yaml") as f:
        dictConfig(yaml.safe_load(f))

    data = configparser.ConfigParser()
    data.read('local/example.ini')
    keys = [i for i in data['CONFIG']]
    vals = [data['CONFIG'][i] for i in data['CONFIG']]

    conf = ORMConfig(**(dict(zip(keys, vals))))
    conf.project_id = None
    print(conf)

    yt_api = YouTrackAsyncAPI()
    
    try:
        conf = await yt_api.validate_credentials(conf)
        print(conf)
        issue: YTIssue = await yt_api.create_issue(conf, "epsolon 1", "teta 1")
        print(issue)

        issue: YTIssue = await yt_api.update_issue(conf, issue, "formatted string to re.sub")
        print(issue)

        descr: str = await yt_api.get_issue_description(conf, issue)
        print(descr)
    except YouTrackError as e:
        print(str(e))

    await yt_api.__aexit__()

    

asyncio.run(main())