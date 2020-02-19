import logging
import re
from collections import namedtuple
from enum import IntEnum, auto
from functools import wraps
from typing import Dict, Optional, Tuple

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Dispatcher,
    Filters,
    MessageHandler,
)

from bot.db import (
    TelegramUser,
    create_article,
    create_telegram_user,
    get_telegram_user,
    update_telegram_user_context,
    create_user_settings,
    get_user_articles,
)

logger = logging.getLogger(__name__)

SIZE_RE = re.compile("[0-9]{1,2}")

MIN_LIST_SIZE = 3
MAX_LIST_SIZE = 10

LIST_SIZE = "list_size"
ARTICLE_TTL = "article_ttl"
SETTINGS_PROVIDED = "settings_provided"

WELCOME_MSG = """Hi!
I am ReadingListBot. We have not met before.
I can manage your reading list, follow instructions to create one.
"""

ASK_FOR_LIST_SIZE_MSG = f"""
Provide size of your reading list, number between {MIN_LIST_SIZE} and {MAX_LIST_SIZE} (including boundaries).
"""

ASK_FOR_ITEM_TTL_MSG = """
How long should article stay in the reading list?
"""

ASK_FOR_ARTICLE_MSG = "Provide article text or link to an article."

ARTICLE_CREATED_MSG = "Article successfully created."

LIST_IS_FULL_MSG = "List is full, you can not add more articles."

ARTICLE_ALREADY_EXISTS_MSG = "Article already exists."

ERROR_MSG = "Sorry, there was an error"

SHOW_COMMANDS_MSG = """Hello again! You can execute the following commands:
/start
/add_article
/show_commands
"""

days_keyboard = ReplyKeyboardMarkup(["3", "5", "7"], one_time_keyboard=True)


class State(IntEnum):
    WELCOME = auto()
    SHOW_COMMANDS = auto()
    WAITING_FOR_LIST_SIZE = auto()
    WAITING_FOR_ARTILCE_TTL = auto()
    ADD_ARTICLE = auto()


Reply = namedtuple("Reply", ["msg", "reply_markup"])

DEFAULT_MSG = Reply(WELCOME_MSG, None)

STATE_MSG = {
    State.WAITING_FOR_LIST_SIZE: Reply(ASK_FOR_LIST_SIZE_MSG, None),
    State.WAITING_FOR_ARTILCE_TTL: Reply(ASK_FOR_ITEM_TTL_MSG, days_keyboard),
    State.ADD_ARTICLE: Reply(ASK_FOR_ARTICLE_MSG, None),
    State.SHOW_COMMANDS: Reply(SHOW_COMMANDS_MSG, None),
}


def get_state_msg(state: State) -> Tuple[str, Dict]:
    msg, reply_markup = STATE_MSG.get(state, DEFAULT_MSG)
    reply_kwargs = {}
    if reply_markup is not None:
        reply_kwargs.update(reply_markup=reply_markup)
    return msg, reply_kwargs


def get_next_state(context: dict) -> State:
    state = context["state"]
    if state == State.WELCOME:
        if SETTINGS_PROVIDED in context:
            return ConversationHandler.END
        else:
            return State.WAITING_FOR_LIST_SIZE
    elif state == State.WAITING_FOR_LIST_SIZE:
        if LIST_SIZE in context:
            return State.WAITING_FOR_ARTILCE_TTL
        else:
            return State.WAITING_FOR_LIST_SIZE
    elif state == State.WAITING_FOR_ARTILCE_TTL:
        if ARTICLE_TTL in context:
            return State.ADD_ARTICLE
        else:
            return State.WAITING_FOR_ARTILCE_TTL
    elif state == State.ADD_ARTICLE:
        return State.ADD_ARTICLE
    else:
        return ConversationHandler.END


def log_error(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception("Got exception %s", e)
            raise e

    return wrapper


def get_info_msg(user: TelegramUser) -> str:
    articles = get_user_articles(user.id)
    msg = f"Hello {user.first_name}! You have {len(articles)} unread articles. Type /show_commands for a list of commands."
    return msg


@log_error
def welcome(update: Update, context: CallbackContext) -> State:
    logger.debug("welcome")
    telegram_id = update.message.from_user.id
    logger.debug("Telegram User %s", telegram_id)
    user = get_telegram_user(telegram_id)
    logger.debug("User context %s", user.context if user else None)
    if user:
        next_state = get_next_state(user.context)
        logger.debug("State %s", next_state)
        if next_state == ConversationHandler.END:
            msg = get_info_msg(user)
            update.message.reply_text(msg)
            return ConversationHandler.END

        update_telegram_user_context(telegram_id, {"state": next_state})
        msg, reply_kwargs = get_state_msg(next_state)
        update.message.reply_text(msg, **reply_kwargs)
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


@log_error
def waiting_for_list_size(update: Update, context: CallbackContext) -> State:
    telegram_id = update.message.from_user.id
    size = get_list_size(update.message.text)
    ctx = {}
    state = State.WAITING_FOR_LIST_SIZE
    is_size_valid = size >= MIN_LIST_SIZE and size <= MAX_LIST_SIZE

    if size is not None and is_size_valid:
        state = State.WAITING_FOR_ARTILCE_TTL
        ctx.update(list_size=size)

    ctx.update(state=state)
    update_telegram_user_context(telegram_id, ctx)
    msg, reply_kwargs = get_state_msg(state)
    update.message.reply_text(msg, **reply_kwargs)
    return state


def get_articel_ttl(msg: str) -> int:
    try:
        return int(msg)
    except ValueError:
        pass


@log_error
def waiting_for_artilce_ttl(update: Update, context: CallbackContext) -> State:
    telegram_id = update.message.from_user.id
    article_ttl = get_articel_ttl(update.message.text)
    ctx = {}
    state = State.WAITING_FOR_ARTILCE_TTL

    if article_ttl:
        user = get_telegram_user(telegram_id)
        list_size = user.context.get(LIST_SIZE)
        if list_size is None:
            update.message.reply_text(ERROR_MSG)
            return State.WAITING_FOR_LIST_SIZE
        else:
            settings = create_user_settings(user, list_size, article_ttl)
            if settings is None:
                update.message.reply_text(ERROR_MSG)
                return State.WAITING_FOR_ARTILCE_TTL

        state = State.ADD_ARTICLE
        ctx.update(article_ttl=article_ttl, settings_provided=True)

    ctx.update(state=state)
    update_telegram_user_context(telegram_id, ctx)
    msg, reply_kwargs = get_state_msg(state)
    update.message.reply_text(msg, **reply_kwargs)
    return state


def check_and_create_article(user: TelegramUser, update: Update) -> (str, State):
    articles = get_user_articles(user.id)
    settings = user.settings[0]
    if len(articles) >= settings.reading_list_size:
        return LIST_IS_FULL_MSG, State.WELCOME

    new_article_text = update.message.text
    old_article = [a for a in articles if a.text == new_article_text]
    if len(old_article) > 0:
        return ARTICLE_ALREADY_EXISTS_MSG, State.WELCOME

    article = create_article(user, new_article_text)
    if article is None:
        return ERROR_MSG, State.ADD_ARTICLE

    return ARTICLE_CREATED_MSG, State.WELCOME


@log_error
def add_article(update: Update, context: CallbackContext) -> State:
    telegram_id = update.message.from_user.id
    user = get_telegram_user(telegram_id)
    state = State.WELCOME
    msg = None
    ctx = {}

    if user is None:
        logger.error("User not found by id: %s", telegram_id)
        msg = ERROR_MSG
        state = State.WELCOME
    else:
        msg, state = check_and_create_article(user, update)

    ctx.update(state=state)
    update_telegram_user_context(telegram_id, ctx)
    msg = msg or ERROR_MSG
    update.message.reply_text(msg)
    return state


@log_error
def show_commands(update: Update, context: CallbackContext) -> State:
    logger.debug("show_commands")
    update.message.reply_text(SHOW_COMMANDS_MSG)
    return ConversationHandler.END


def error(update: Update, context: CallbackContext) -> None:
    logger.error('Update "%s" caused error "%s"', update, context.error)


def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", welcome),
            CommandHandler("add_article", add_article),
            CommandHandler("show_commands", show_commands)
        ],
        states={
            State.WELCOME: [MessageHandler(Filters.all, welcome)],
            State.WAITING_FOR_LIST_SIZE: [
                MessageHandler(Filters.regex("[0-9]{1,2}"), waiting_for_list_size)
            ],
            State.WAITING_FOR_ARTILCE_TTL: [
                MessageHandler(Filters.regex("[0-9]{1}"), waiting_for_artilce_ttl)
            ],
            State.ADD_ARTICLE: [MessageHandler(Filters.text, add_article)],
            State.SHOW_COMMANDS: [MessageHandler(Filters.all, show_commands)],
        },
        fallbacks=[CommandHandler("cancel", show_commands)]
    )


def set_handlers(dp: Dispatcher):
    dp.add_handler(get_conversation_handler())
    dp.add_error_handler(error)
