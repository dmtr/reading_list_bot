import logging

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Dispatcher,
)

logger = logging.getLogger(__name__)

START_MESSAGE = """Hi!
I am ReadingListBot.
"""


def start(update: Update, context: CallbackContext):
    update.message.reply_text(START_MESSAGE)


def error(update: Update, context: CallbackContext):
    logger.error('Update "%s" caused error "%s"', update, context.error)


def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(entry_points=[CommandHandler("start", start)])


def set_handlers(dp: Dispatcher):
    dp.add_handler(get_conversation_handler())
    dp.add_error_handler(error)
