import logging
import os
from typing import Any, Dict, Optional, Tuple

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
    TextField
)
from playhouse.pool import PooledPostgresqlExtDatabase
from playhouse.postgres_ext import BinaryJSONField

logger = logging.getLogger(__name__)
MAX_CONNECTIONS = 10
STALE_TIMEOUT = 300

ARTICLE_STATUSES = ("NEW", "READ")

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


class Article(BaseModel):
    created_at = DateTimeField(constraints=[SQL("DEFAULT now()")], index=True)
    status = EnumField(ARTICLE_STATUSES)
    text = TextField()

    class Meta:
        table_name = "article"


class TelegramUser(BaseModel):
    created_at = DateTimeField(constraints=[SQL("DEFAULT now()")])
    first_name = CharField()
    telegram_id = BigIntegerField(unique=True)
    context = BinaryJSONField(null=True)

    class Meta:
        table_name = "telegram_user"


class UserArticleM2M(BaseModel):
    article = ForeignKeyField(
        column_name="article_id", field="id", model=Article, null=True
    )
    user = ForeignKeyField(
        column_name="user_id", field="id", model=TelegramUser, null=True
    )

    class Meta:
        table_name = "user_article_m2m"
        primary_key = False


class UserSettings(BaseModel):
    article_ttl_in_days = IntegerField()
    reading_list_size = IntegerField()
    user = ForeignKeyField(
        column_name="user_id", field="id", model=TelegramUser, null=True
    )

    class Meta:
        table_name = "user_settings"
        primary_key = False


def get_telegram_user(telegram_id: int) -> Optional[TelegramUser]:
    try:
        return TelegramUser.get(TelegramUser.telegram_id == telegram_id)
    except DoesNotExist:
        return None


@db.atomic()
def create_telegram_user(telegram_id: int, first_name: str, context: Dict) -> Optional[TelegramUser]:
    try:
        return TelegramUser.create(telegram_id=telegram_id, first_name=first_name, context=context)
    except IntegrityError as e:
        logger.error('Can not create user %s', e)
        return None


@db.atomic()
def update_telegram_user_context(telegram_id: int, context: Dict) -> Optional[TelegramUser]:
    try:
        user = get_telegram_user(telegram_id)
        if user:
            user.context.update(context)
            user.save()
    except DatabaseError as e:
        logger.error('Can not update user %s', e)
        return None
