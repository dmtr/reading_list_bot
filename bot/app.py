import logging
import os

from typing import Dict
from telegram.ext import Updater
from bot.handlers import set_handlers
from bot.db import get_db

logger = logging.getLogger(__name__)


def get_config() -> Dict:
    return {
        "token": os.environ.get("TOKEN"),
    }


def create_updater() -> Updater:
    conf = get_config()
    updater = Updater(conf["token"], use_context=True)
    set_handlers(updater.dispatcher)
    updater.dispatcher.db = get_db()
    return updater


def run() -> None:
    logger.info('Starting up')
    u = create_updater()
    u.start_polling()
    u.idle()
