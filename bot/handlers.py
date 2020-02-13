import logging
import re
from enum import IntEnum, auto
from typing import Optional

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Dispatcher,
    Filters,
    MessageHandler,
)

from bot.db import create_telegram_user, get_telegram_user, update_telegram_user_context

logger = logging.getLogger(__name__)

SIZE_RE = re.compile("[0-9]{1,2}")

WELCOME_MSG = """Hi!
I am ReadingListBot. We have not met before.
I can manage your reading list, follow instructions to create one.
"""

ASK_FOR_LIST_SIZE_MSG = """
Provide size of your reading list, number between 3 and 10.
"""

ASK_FOR_ITEM_TTL_MSG = """
How long should article stay in the reading list?.
"""


class State(IntEnum):
    WELCOME = auto()
    SHOW_COMMANDS = auto()
    WAITING_FOR_LIST_SIZE = auto()
    WAITING_FOR_ARTILCE_TTL = auto()


STATE_MSG = {
    State.WAITING_FOR_LIST_SIZE: ASK_FOR_LIST_SIZE_MSG,
    State.WAITING_FOR_ARTILCE_TTL: ASK_FOR_ITEM_TTL_MSG,
}


def get_next_state(state: State) -> State:
    if state == State.WELCOME:
        return State.WAITING_FOR_LIST_SIZE
    else:
        return State.WELCOME


def get_state_msg(state: State) -> str:
    return STATE_MSG.get(state, WELCOME_MSG)


def welcome(update: Update, context: CallbackContext):
    telegram_id = update.message.from_user.id
    logger.debug("Telegram User %s", telegram_id)
    user = get_telegram_user(telegram_id)
    logger.debug("DB user %s", user)
    if user:
        state = user.context["state"]
        next_state = get_next_state(state)
        logger.debug("State %s", next_state)
        msg = get_state_msg(next_state)
        update.message.reply_text(msg)
        return next_state
    else:
        user = create_telegram_user(
            telegram_id, update.message.from_user.first_name, {"state": State.WELCOME}
        )
        if user is None:
            return State.WELCOME

        update.message.reply_text(f"{WELCOME_MSG} {ASK_FOR_LIST_SIZE_MSG}")
        return State.WAITING_FOR_LIST_SIZE


def get_list_size(msg: str) -> Optional[int]:
    try:
        return int(SIZE_RE.findall(msg)[0])
    except (IndexError, ValueError):
        pass


def waiting_for_list_size(update: Update, context: CallbackContext):
    size = get_list_size(update.message.text)
    if size is None:
        update.message.reply_text(ASK_FOR_LIST_SIZE_MSG)
        return State.WELCOME
    else:
        telegram_id = update.message.from_user.id
        ctx = {"state": State.WAITING_FOR_ARTILCE_TTL, "list_size": size}
        update_telegram_user_context(telegram_id, ctx)
        update.message.reply_text(ASK_FOR_ITEM_TTL_MSG)
        return State.WAITING_FOR_ARTILCE_TTL


def waiting_for_artilce_ttl(update: Update, context: CallbackContext):
    update.message.reply_text(update.message.text)
    return State.WELCOME


def error(update: Update, context: CallbackContext):
    logger.error('Update "%s" caused error "%s"', update, context.error)


def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", welcome)],
        states={
            State.WELCOME: [MessageHandler(Filters.all, welcome)],
            State.WAITING_FOR_LIST_SIZE: [
                MessageHandler(Filters.regex("[0-9]{1,2}"), waiting_for_list_size)
            ],
            State.WAITING_FOR_ARTILCE_TTL: [
                MessageHandler(Filters.text, waiting_for_artilce_ttl)
            ],
        },
        fallbacks=[MessageHandler(Filters.all, welcome)],
    )


def set_handlers(dp: Dispatcher):
    dp.add_handler(get_conversation_handler())
    dp.add_error_handler(error)
