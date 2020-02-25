import logging
import os
from typing import Any, Dict, Optional, Tuple, List

from peewee import (
    SQL,
    BigIntegerField,
    CharField,
    DateTimeField,
    DoesNotExist,
    ForeignKeyField,
    IntegerField,
    IntegrityError,
    DatabaseError,
    Model,
    TextField,
)
from playhouse.pool import PooledPostgresqlExtDatabase
from playhouse.postgres_ext import BinaryJSONField

logger = logging.getLogger(__name__)
MAX_CONNECTIONS = 10
STALE_TIMEOUT = 300

ARTICLE_STATUS_NEW = "NEW"
ARTICLE_STATUS_READ = "READ"
ARTICLE_STATUSES = (ARTICLE_STATUS_NEW, ARTICLE_STATUS_READ)

db = PooledPostgresqlExtDatabase(None)


def get_connection_params() -> Dict:
    return {
        "host": os.environ.get("POSTGRES_HOST"),
        "port": int(os.environ.get("POSTGRES_PORT")),
        "user": os.environ.get("POSTGRES_USER"),
        "password": os.environ.get("POSTGRES_PASSWORD"),
        "dbname": os.environ.get("POSTGRES_DBNAME"),
    }


def get_connection_url() -> str:
    params = get_connection_params()
    url = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['dbname']}"
    return url


def get_db() -> PooledPostgresqlExtDatabase:
    params = get_connection_params()
    dbname = params.pop("dbname")
    db.init(
        dbname, max_connections=MAX_CONNECTIONS, stale_timeout=STALE_TIMEOUT, **params
    )
    return db


class EnumField(CharField):
    def __init__(self, choices: Tuple, *args: Any, **kwargs: Any) -> None:
        super(CharField, self).__init__(*args, **kwargs)
        self.choices = choices
        self.max_length = 255

    def adapt(self, value: Any) -> Any:
        if value not in self.choices:
            raise TypeError("Wrong choice")

        return value


class BaseModel(Model):
    class Meta:
        database = db


class TelegramUser(BaseModel):
    created_at = DateTimeField(constraints=[SQL("DEFAULT now()")])
    first_name = CharField()
    telegram_id = BigIntegerField(unique=True)
    context = BinaryJSONField(null=True)

    class Meta:
        table_name = "telegram_user"


class Article(BaseModel):
    created_at = DateTimeField(constraints=[SQL("DEFAULT now()")], index=True)
    status = EnumField(ARTICLE_STATUSES)
    text = TextField()
    user = ForeignKeyField(
        column_name="user_id", field="id", model=TelegramUser, backref="articles"
    )

    class Meta:
        table_name = "article"


class UserSettings(BaseModel):
    article_ttl_in_days = IntegerField()
    reading_list_size = IntegerField()
    email = CharField(null=True)
    user = ForeignKeyField(
        column_name="user_id",
        field="id",
        model=TelegramUser,
        null=True,
        backref="settings",
    )

    class Meta:
        table_name = "user_settings"
        primary_key = False


@db.atomic()
def get_telegram_user(telegram_id: int) -> Optional[TelegramUser]:
    try:
        return TelegramUser.get(TelegramUser.telegram_id == telegram_id)
    except DoesNotExist:
        return None


@db.atomic()
def create_telegram_user(
    telegram_id: int, first_name: str, context: Dict
) -> Optional[TelegramUser]:
    try:
        return TelegramUser.create(
            telegram_id=telegram_id, first_name=first_name, context=context
        )
    except IntegrityError as e:
        logger.error("Can not create user %s", e)
        return None


@db.atomic()
def update_telegram_user_context(
    telegram_id: int, context: Dict
) -> Optional[TelegramUser]:
    try:
        user = get_telegram_user(telegram_id)
        if user:
            user.context.update(context)
            user.save()
    except DatabaseError as e:
        logger.error("Can not update user %s", e)
        return None


@db.atomic()
def create_article(user: TelegramUser, text: str) -> Optional[Article]:
    try:
        return Article.create(text=text, status=ARTICLE_STATUS_NEW, user_id=user.id)
    except DatabaseError as e:
        logger.error("Can not create article %s", e)
        return None


@db.atomic()
def create_user_settings(
    user: TelegramUser, reading_list_size: int, article_ttl_in_days: int
) -> Optional[UserSettings]:
    try:
        return UserSettings.create(
            user_id=user.id,
            reading_list_size=reading_list_size,
            article_ttl_in_days=article_ttl_in_days,
        )
    except DatabaseError as e:
        logger.error("Can not create settings for user %s %s", user, e)
        return None


@db.atomic()
def get_user_articles(user_id: int, status: str = ARTICLE_STATUS_NEW) -> List[Article]:
    try:
        articles = Article.select().where(
            (Article.user_id == user_id) & (Article.status == status)
        )
        return [a for a in articles]
    except DatabaseError as e:
        logger.error("Can not get articles %s", e)
        return []


@db.atomic()
def get_article(article_id: int) -> Optional[Article]:
    try:
        return Article.get(Article.id == article_id)
    except DoesNotExist:
        return None


@db.atomic()
def update_article_status(
    article_id: int, status: str
) -> Optional[TelegramUser]:
    try:
        article = get_article(article_id)
        if article:
            article.status = status
            article.save()
            return article
    except DatabaseError as e:
        logger.error("Can not update article %s status %s", article_id, e)
        return None
