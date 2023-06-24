from youtrack_reporter.app.youtrack import YouTrackAsyncAPI

from youtrack_reporter.app.server import run
from youtrack_reporter.app.settings import load_app_settings

import yaml

import logging
from logging.config import dictConfig
import coloredlogs

if __name__=="__main__":

    with open("logging.yaml") as f:
        dictConfig(yaml.safe_load(f))

    settings = load_app_settings()
    run(settings)